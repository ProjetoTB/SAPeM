//////////////////////////////////////////////////////////////////////
//////////////////// reports.html javascript file ////////////////////
reportVars = {
	"idade": "Faixa etária"
};

us_ids = new Array();

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
			var content = $("<div>")
				              .attr("id", "formId_"+ form_id[f])
							  .appendTo($("#tabs"))
							  .addClass("formDivs");
		}
	}

	$.fn.createFieldset = function(label, variable, form_id){
		var fieldset = $("<fieldset>")
			               .appendTo($("#formId_" + form_id))
						   .addClass("filtros");
		var legend = $("<legend>")
			               .appendTo(fieldset)
						   .text(label);
		var chartDiv = $("<div>")
			               .appendTo(fieldset)
						   .attr("id", "chart_" + variable + "_" + form_id);
		//var chart = $().drawChart(variable, form_id, us_ids);
	}

	$.fn.drawChart = function(variable, form_id){
		url = getUrlbase() + "reports/getData/" + getConfigId() + "/" + form_id + "/" + variable + "/?us=" + us_ids;

		var legend = new Array();
		var values = new Array();

		if (variable == "idade"){
			$.getJSON(url, function(statistics){
					$.each(statistics, function(key, val) {
						legend[legend.length] = key + ": %%.%%";
						values[values.length] = parseInt(statistics[key], 10);
					});
					var chart = Raphael("chart_" + variable + "_" + form_id),
						pie = chart.piechart(110, 130, 100,
											 values,
											 { legend: legend,
											   legendpos: "east"
											   //colors: ["#blue", "#red", "#yellow", "#gray", "#brown"]
											 });
					//TO-DO: search how to change the colors order
					// Copied from: http://raphaeljs.com
					pie.hover(function () {
						this.sector.stop();
						this.sector.scale(1.1, 1.1, this.cx, this.cy);

						if (this.label) {
							this.label[0].stop();
							this.label[0].attr({ chart: 7.5 });
							this.label[1].attr({ "font-weight": 800});
							this.label[1].attr({ "font-size": 16});
						}
					}, function () {
						this.sector.animate({ transform: 's1 1 ' + this.cx + ' ' + this.cy }, 500, "bounce");

						if (this.label) {
							this.label[0].animate({ chart: 5 }, 500, "bounce");
							this.label[1].attr({ "font-weight": 400 });
							this.label[1].attr({ "font-size": 12 });
						}
					});
				})
				.error( function() {
					var errosMsg = $("<p>")
								   .appendTo($("#chart_" + variable + "_" + form_id))
								   .text("Nenhuma ficha foi encontrada!");
				})
		}
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

				unidades = xml.getElementsByTagName('settings')[0].getElementsByTagName('unidadeSaude')[0].childNodes;
				for (u=0; u < unidades.length; u++)
					us_ids[u] = (unidades[u].childNodes[0].nodeValue);
			}

			$().retrieveFormNames(form_id);

			for (id=0; id < form_id.length; id++)
				$.each(reportVars, function(k, val){
					$().createFieldset(reportVars[k], k, form_id[id]);

					if (id==0)
						$().drawChart(k, form_id[id]);
				});


			$("#tabs").tabs({
				select: function(event, tab) {
							$.each(reportVars, function(key, val) {
								if ($("#chart_" + key + "_" + tab.panel.id.split('_')[1]).html() == '')
									$().drawChart(key, tab.panel.id.split('_')[1]);
							});
						}
			});
		}
	});
});
