from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required
from ..models import ProductArea

@staff_member_required
def get_nodes(request):
    exclude_id = request.GET.get('exclude')
    nodes = ProductArea.objects.exclude(id=exclude_id).select_related('parent')
    return JsonResponse([{'id': node.id, 'name': node.name, 'depth': node.get_depth()} for node in nodes], safe=False)

@require_POST
@staff_member_required
def move_node(request, node_id):
    node = ProductArea.objects.get(id=node_id)
    parent_id = request.POST.get('parent')
    if parent_id:
        parent = ProductArea.objects.get(id=parent_id)
        node.move(parent)
    else:
        node.move(None)  # Move to root
    return JsonResponse({'status': 'success'})
