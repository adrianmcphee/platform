from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.db.models import Q, Prefetch
from .fields import Base58UUIDv5Field
from abc import ABC, ABCMeta
from apps.commerce.interfaces import BountyPurchaseInterface


class AttachmentAbstract(models.Model):
    attachments = models.ManyToManyField("product_management.FileAttachment", blank=True)

    class Meta:
        abstract = True

class TreeNode(models.Model):
    id = Base58UUIDv5Field(primary_key=True)
    path = models.TextField(db_index=True)
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    def save(self, *args, **kwargs):
        if self.parent:
            self.path = f"{self.parent.path}/{self.id}"
        else:
            self.path = self.id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.path})"

    @classmethod
    def get_root_nodes(cls):
        return cls.objects.filter(parent__isnull=True)

    def get_children(self):
        """Get immediate children using foreign key relationship."""
        return self.children.all()

    def get_children_by_path(self):
        """Get immediate children using path-based query."""
        return self.__class__.objects.filter(
            path__startswith=f"{self.path}/",
            path__regex=f"^{self.path}/[^/]+$"
        )

    def get_descendants(self, include_self=False):
        if include_self:
            return self.__class__.objects.filter(path__startswith=self.path)
        return self.__class__.objects.filter(path__startswith=f"{self.path}/")

    def get_ancestors(self, include_self=False):
        if include_self:
            return self.__class__.objects.filter(path__in=self.path.split('/'))
        return self.__class__.objects.filter(path__in=self.path.split('/')[:-1])

    def get_siblings(self, include_self=False):
        if self.parent:
            siblings = self.parent.get_children()
            if not include_self:
                siblings = siblings.exclude(id=self.id)
            return siblings
        return self.__class__.objects.filter(parent__isnull=True).exclude(id=self.id)

    def is_root(self):
        return self.parent is None

    def is_leaf(self):
        return not self.get_children().exists()

    def get_root(self):
        return self.get_ancestors().first() or self

    def get_depth(self):
        return len(self.path.split('/'))

    @classmethod
    def get_tree(cls, root=None):
        if root:
            return root.get_descendants(include_self=True)
        return cls.objects.all()

    def move(self, target_parent):
        old_path = self.path
        self.parent = target_parent
        self.save()
        descendants = self.get_descendants()
        for descendant in descendants:
            descendant.path = descendant.path.replace(old_path, self.path, 1)
        self.__class__.objects.bulk_update(descendants, ['path'])

    @classmethod
    def get_with_children(cls, node_id):
        """
        Fetch a node with its children prefetched.
        
        This method efficiently retrieves a node and its immediate children
        in a single query, reducing database hits.
        
        :param node_id: The ID of the node to fetch
        :return: A TreeNode instance with prefetched children
        """
        return cls.objects.prefetch_related(
            Prefetch('children', queryset=cls.objects.order_by('path'))
        ).get(id=node_id)

    @classmethod
    def get_with_descendants(cls, node_id, depth=1):
        """
        Fetch a node with its descendants prefetched to a specified depth.
        
        :param node_id: The ID of the node to fetch
        :param depth: The depth of descendants to prefetch (default is 1, immediate children only)
        :return: A TreeNode instance with prefetched descendants
        """
        def prefetch_descendants(current_depth):
            if current_depth <= 0:
                return []
            return [Prefetch('children', queryset=cls.objects.order_by('path'),
                             to_attr=f'_prefetched_children_depth_{current_depth}')]
        
        prefetch_query = prefetch_descendants(depth)
        for d in range(depth - 1, 0, -1):
            prefetch_query[0].queryset = prefetch_query[0].queryset.prefetch_related(prefetch_descendants(d))
        
        return cls.objects.prefetch_related(*prefetch_query).get(id=node_id)

    class Meta:
        abstract = True
        ordering = ['path']
        indexes = [
            models.Index(fields=['path']),
        ]

class DjangoABCMeta(models.base.ModelBase, ABCMeta):
    pass
