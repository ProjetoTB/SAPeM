
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


/*
	perguntasTable = $('#perguntas_table').dataTable({
		"iDisplayLength": 100,
		"sDom": 't<"clear">',
		"bSort": false
	});
*/
/*
	$('#formulario').change(function(){
		perguntasTable.fnClearTable();
		var urlString = $(location).attr('href') + $(this).val() + '/';
		window.setTimeout(function(){$.ajax({
			type: 'POST',
			url: urlString,
			dataType: "xml",
			success: function(xml){
				var elements = xml.getElementsByTagName('questions')[0].childNodes;
				$(elements).each(function(){
					var el = $(this).get(0);
					if($(el)[0].nodeType == xml.ELEMENT_NODE){
						perguntasTable.fnAddData(
						["<input type='checkbox' value='"+ $(el)[0].tagName +"'/>", $(el).text()]
						);
					}
				});
			}
		})});
	});
*/
});
