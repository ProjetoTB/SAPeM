//////////////////////////////////////////////////////////////////////
//////////////////// reports.html javascript file ////////////////////
reportVars = {
	"idade": "Faixa etária",
	"tosse": "Tosse"
};

function getUrlArray(){
	var urlString = $(location).attr('href');
	var urlArray = urlString.split('/');

	return urlArray;
}

function getUrlbase(){
	//Make the urlbase (necessary case SAPeM migrate to another server)
	var urlArray = getUrlArray();
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
	urlbase += '/';
	return urlbase;
}

function getConfigId(){
	var urlArray = getUrlArray();
	return urlArray[urlArray.length - 2];
}

$(document).ready(function(){
	$.fn.retrieveFormNames = function(form_id){
		var ul = $("<ul>").appendTo($("#tabs"));
		for (f=0; f < form_id.length; f ++){
			var li = $('<li>').appendTo(ul);
			var a  = ($('<a>'))
						   .appendTo(li)
						   .attr('href', '#formId_' + form_id[f]);
			$.ajax({
				type: 'POST',
				url:   getUrlbase() + 'form/names/' + form_id[f] + '/',
				dataType: 'text',
				cache: false,
				success: (
					function(link_elem) {
						return function(formName){
							link_elem.text(formName);
						}
					})(a)
			});
			var content = $("<div>").attr("id", "formId_"+ form_id[f])
			content.appendTo($("#tabs"));
		}
		$('#tabs').tabs();
	}

	$.fn.createFieldset = function(label, form_id){
		var fieldset = $("<fieldset>")
			               .appendTo($("#formId_" + form_id))
						   .addClass("filtros");
		var legend = $("<legend>")
			               .appendTo(fieldset)
						   .text(label);
	}
	
	urlbase  = getUrlbase();
	configId = getConfigId();
	url      = urlbase + 'reports/configSettingXml/'+ configId +'/';

	form_id = new Array();

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
					form_id[f] = (forms[f].childNodes[0].nodeValue);
			}
			$().retrieveFormNames(form_id);
			for (id=0; id < form_id.length; id++){
				for (k in reportVars)
					$().createFieldset(reportVars[k], form_id[id]);
			}
		}
	});
});
