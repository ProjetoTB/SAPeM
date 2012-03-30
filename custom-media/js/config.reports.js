$(document).ready(function(){
	var formTable = $('#form_table').dataTable({
		"iDisplayLength": 100,
		"sDom": 't<"clear">',
		"bSort": false
	});

	$('#unidadesSaude_table').dataTable({
		"iDisplayLength": 100,
		"sDom": 't<"clear">'
	});
	$('#form_configReport').validate({});
});
