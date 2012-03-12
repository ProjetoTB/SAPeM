forms_id         = new Array();
unidadesSaude_id = new Array();

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
	//////////////////////////////////////////////////////////////////////
	//////////////////// reports.html javascript file ////////////////////
	
	// Parsing settings xml from stored configuration...
	//Make the urlbase (necessary case SAPeM migrate to another server) 
	var urlString = $(location).attr('href');
	var urlArray = urlString.split('/');
	var indexToRunUrlString = 0; 
	var urlbase = '';
	for (indexToRunUrlString in urlArray)
		if (urlArray[indexToRunUrlString] == 'sapem')
			var indexToRecord = indexToRunUrlString;
	for (indexToRunUrlString in urlArray.slice(0,parseInt(indexToRecord,10) + 1))
		if (indexToRunUrlString == 0)
			urlbase += urlArray[indexToRunUrlString];
		else
			urlbase += '/' + urlArray[indexToRunUrlString];
	urlbase  += '/';
	configId = urlArray[urlArray.length - 2];
	url      = urlbase + 'reports/configSettingXml/'+ configId +'/';
	$.ajax({
		type: 'POST',
		url: url,
		dataType: "html",
		cache: false,
		success: function(text){
			if (window.DOMParser){
				parser=new DOMParser();
				xml=parser.parseFromString(text,"text/xml");
			}
			else{ // Internet Explorer
				xml=new ActiveXObject("Microsoft.XMLDOM");
				xml.async="false";
				xml.loadXML(text);
			}
			if (xml.getElementsByTagName('error')[0] == undefined){
				forms = xml.getElementsByTagName('settings')[0].getElementsByTagName('formularios')[0].childNodes;
				for (f=0; f < forms.length; f++)
					forms_id[f] = forms[f].childNodes[0].nodeValue;

				unidades = xml.getElementsByTagName('settings')[0].getElementsByTagName('unidadeSaude')[0].childNodes;
				for (us=0; us < unidades.length; us++)
					unidadesSaude_id[us] = unidades[us].childNodes[0].nodeValue;
			}
		}
	});
	// Done parsing settings
	
	//////////////////////////////////////////////////////////////////////
	//////////////////// Validation Plugin //////////////////////////////
	$('#form_configReport').validate({});
});
