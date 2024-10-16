(function($) {
    $(document).ready(function() {
        var $moveForm = $('<form id="move-node-form">' +
            '<select name="parent" id="parent-select">' +
            '<option value="">Move to root</option>' +
            '</select>' +
            '<input type="submit" value="Move">' +
            '</form>');

        $('.move_node').click(function(e) {
            e.preventDefault();
            var $row = $(this).closest('tr');
            var nodeId = $row.find('input[name="_selected_action"]').val();

            // Populate select with all nodes except the current one and its descendants
            $.get('/admin/product_management/productarea/get_nodes/?exclude=' + nodeId, function(data) {
                $('#parent-select').html('<option value="">Move to root</option>');
                data.forEach(function(node) {
                    $('#parent-select').append($('<option>', {
                        value: node.id,
                        text: '—'.repeat(node.depth) + ' ' + node.name
                    }));
                });
            });

            $moveForm.dialog({
                title: 'Move Node',
                modal: true,
                buttons: {
                    "Move": function() {
                        var parentId = $('#parent-select').val();
                        $.post('/admin/product_management/productarea/' + nodeId + '/move/', 
                               {parent: parentId, csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()},
                               function(data) {
                                   location.reload();
                               });
                        $(this).dialog("close");
                    },
                    "Cancel": function() {
                        $(this).dialog("close");
                    }
                }
            });
        });

        $('body').append($moveForm);
    });
})(django.jQuery);

