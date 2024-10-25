import logging
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.apps import apps

from ..interfaces import ProductAreaServiceInterface
from ..models import (
    ProductArea,
    ProductTree,
    Product,
    Challenge
)

logger = logging.getLogger(__name__)

class ProductAreaService(ProductAreaServiceInterface):
    def create_node(
        self,
        product_id: str,
        name: str,
        parent_id: Optional[str],
        details: Dict
    ) -> Tuple[bool, str, Optional[str]]:
        """Create a new product area node"""
        try:
            with transaction.atomic():
                # Validate product
                product = Product.objects.get(id=product_id)

                # Get or create product tree
                product_tree = product.product_trees.first()
                if not product_tree:
                    product_tree = ProductTree.objects.create(
                        name=f"{product.name} Tree",
                        product=product
                    )

                # Convert video URL if present
                if video_url := details.get('video_link'):
                    from .services import ProductService
                    details['video_link'] = ProductService.convert_youtube_link_to_embed(video_url)

                # Create node
                if parent_id:
                    parent = ProductArea.objects.get(id=parent_id)
                    if parent.product_tree.product_id != product_id:
                        return False, "Parent node belongs to different product", None
                    
                    node = parent.add_child(
                        name=name,
                        description=details.get('description', ''),
                        video_link=details.get('video_link'),
                        video_name=details.get('video_name'),
                        video_duration=details.get('video_duration'),
                        product_tree=product_tree
                    )
                else:
                    node = ProductArea.add_root(
                        name=name,
                        description=details.get('description', ''),
                        video_link=details.get('video_link'),
                        video_name=details.get('video_name'),
                        video_duration=details.get('video_duration'),
                        product_tree=product_tree
                    )

                return True, "Product area created successfully", node.id

        except (Product.DoesNotExist, ProductArea.DoesNotExist):
            return False, "Product or parent node not found", None
        except Exception as e:
            logger.error(f"Error creating product area: {str(e)}")
            return False, str(e), None

    def move_node(
        self,
        node_id: str,
        new_parent_id: Optional[str]
    ) -> Tuple[bool, str]:
        """Move node in tree structure"""
        try:
            with transaction.atomic():
                node = ProductArea.objects.get(id=node_id)

                if new_parent_id:
                    new_parent = ProductArea.objects.get(id=new_parent_id)
                    
                    # Validate same product tree
                    if node.product_tree_id != new_parent.product_tree_id:
                        return False, "Cannot move between different product trees"
                    
                    # Validate not moving to own descendant
                    if new_parent.is_descendant_of(node):
                        return False, "Cannot move node to its own descendant"
                    
                    node.move(new_parent)
                else:
                    # Move to root
                    node.move(None)

                self._rebuild_tree(node.product_tree_id)
                return True, "Node moved successfully"

        except ProductArea.DoesNotExist:
            return False, "Node not found"
        except Exception as e:
            logger.error(f"Error moving node: {str(e)}")
            return False, str(e)

    def get_tree(
        self,
        product_id: str
    ) -> List[Dict]:
        """Get complete tree structure for product"""
        try:
            product = Product.objects.get(id=product_id)
            product_tree = product.product_trees.first()
            
            if not product_tree:
                return []

            root_nodes = ProductArea.get_root_nodes().filter(product_tree=product_tree)
            return [self._serialize_node(node) for node in root_nodes]

        except Product.DoesNotExist:
            return []
        except Exception as e:
            logger.error(f"Error getting tree: {str(e)}")
            return []

    def update_node(
        self,
        node_id: str,
        details: Dict,
        updater_id: str
    ) -> Tuple[bool, str]:
        """Update node details"""
        try:
            with transaction.atomic():
                node = ProductArea.objects.select_for_update().get(id=node_id)
                
                # Verify updater has permission
                if not self._can_modify_tree(node.product_tree.product_id, updater_id):
                    return False, "No permission to update node"

                # Convert video URL if present
                if video_url := details.get('video_link'):
                    from .services import ProductService
                    details['video_link'] = ProductService.convert_youtube_link_to_embed(video_url)

                # Update fields
                updateable_fields = [
                    'name', 'description', 'video_link',
                    'video_name', 'video_duration'
                ]
                
                for field in updateable_fields:
                    if field in details:
                        setattr(node, field, details[field])

                node.save()
                return True, "Node updated successfully"

        except ProductArea.DoesNotExist:
            return False, "Node not found"
        except Exception as e:
            logger.error(f"Error updating node: {str(e)}")
            return False, str(e)

    def delete_node(
        self,
        node_id: str,
        updater_id: str
    ) -> Tuple[bool, str]:
        """Delete node and handle dependencies"""
        try:
            with transaction.atomic():
                node = ProductArea.objects.get(id=node_id)
                
                # Verify updater has permission
                if not self._can_modify_tree(node.product_tree.product_id, updater_id):
                    return False, "No permission to delete node"

                # Check for challenges using this node
                if Challenge.objects.filter(product_area=node).exists():
                    return False, "Cannot delete node with associated challenges"

                # Handle children
                if node.get_children():
                    return False, "Cannot delete node with children"

                node.delete()
                return True, "Node deleted successfully"

        except ProductArea.DoesNotExist:
            return False, "Node not found"
        except Exception as e:
            logger.error(f"Error deleting node: {str(e)}")
            return False, str(e)

    def get_node_path(
        self,
        node_id: str
    ) -> List[Dict]:
        """Get path from root to node"""
        try:
            node = ProductArea.objects.get(id=node_id)
            return [
                {
                    'id': ancestor.id,
                    'name': ancestor.name,
                    'depth': ancestor.get_depth()
                }
                for ancestor in node.get_ancestors(include_self=True)
            ]

        except ProductArea.DoesNotExist:
            return []
        except Exception as e:
            logger.error(f"Error getting node path: {str(e)}")
            return []

    def _can_modify_tree(self, product_id: str, person_id: str) -> bool:
        """Check if person can modify product tree"""
        try:
            ProductRoleAssignment = apps.get_model('security', 'ProductRoleAssignment')
            return ProductRoleAssignment.objects.filter(
                product_id=product_id,
                person_id=person_id,
                role__in=['ADMIN', 'MANAGER']
            ).exists()
        except Exception:
            return False

    def _rebuild_tree(self, product_tree_id: str) -> None:
        """Rebuild tree structure after changes"""
        try:
            ProductArea.objects.filter(
                product_tree_id=product_tree_id
            ).rebuild()
        except Exception as e:
            logger.error(f"Error rebuilding tree: {str(e)}")

    def _serialize_node(self, node: ProductArea) -> Dict:
        """Serialize node and its children"""
        challenges = Challenge.objects.filter(product_area=node)
        
        serialized = {
            'id': node.id,
            'name': node.name,
            'description': node.description,
            'video_link': node.video_link,
            'video_name': node.video_name,
            'video_duration': node.video_duration,
            'depth': node.get_depth(),
            'path': node.path,
            'challenges': [{
                'id': challenge.id,
                'title': challenge.title,
                'status': challenge.status
            } for challenge in challenges],
            'children': []
        }

        # Recursively serialize children
        for child in node.get_children():
            serialized['children'].append(self._serialize_node(child))

        return serialized

    def get_node_stats(
        self,
        node_id: str
    ) -> Dict:
        """Get statistics for node and its subtree"""
        try:
            node = ProductArea.objects.get(id=node_id)
            
            # Get all nodes in subtree
            subtree_nodes = node.get_descendants(include_self=True)
            node_ids = subtree_nodes.values_list('id', flat=True)

            # Get challenge stats
            challenges = Challenge.objects.filter(product_area_id__in=node_ids)
            challenge_stats = challenges.aggregate(
                total=Count('id'),
                active=Count('id', filter=Q(status=Challenge.ChallengeStatus.ACTIVE)),
                completed=Count('id', filter=Q(status=Challenge.ChallengeStatus.COMPLETED))
            )

            # Calculate completion percentage
            total = challenge_stats['total'] or 1  # Avoid division by zero
            completion_percentage = (challenge_stats['completed'] / total) * 100

            return {
                'node_count': subtree_nodes.count(),
                'depth': node.get_depth(),
                'challenges': challenge_stats,
                'completion_percentage': round(completion_percentage, 1),
                'has_children': node.get_children().exists()
            }

        except ProductArea.DoesNotExist:
            return {}
        except Exception as e:
            logger.error(f"Error getting node stats: {str(e)}")
            return {}