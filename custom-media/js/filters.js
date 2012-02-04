
function loadTable(id){
	table = $('#table' + id).dataTable({
		"iDisplayLength": 100,
		"sDom": 't<"clear">'
	});
}
