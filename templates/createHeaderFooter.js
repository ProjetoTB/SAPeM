// Functions for creating header and footer
var getScript = jQuery.getScript;
jQuery.getScript = function( resources, callback ) {
    var // reference declaration & localization
    length = resources.length,
    handler = function() { counter++; },
    deferreds = [],
    counter = 0,
    idx = 0;
    for ( ; idx < length; idx++ ) {
        deferreds.push(
            getScript( resources[ idx ], handler )
        );
    }
    jQuery.when(deferreds ).then(function() {
        callback && callback();
    });
};

function setup_tracForm(){
    if (! $().tracForm || typeof rpc === "undefined") {
        setTimeout(setup_tracForm, 100);
        return;
    }
    $('#trac').tracForm({
        "base_url"              :"{{MEDIA_URL}}",
        "close_automatically"   :false,
        //"component"             :get_component(),
        //"component_disabled"    :true,
        "email"                 :"projetotb@gruyere.lps.ufrj.br",
        "priority"              :"critical",
        "ticket_created_message":'<a href="/trac/ticket/\{\{ticket_id\}\}">Ticket URL</a>',
        "type"                  :"bug-fix",
        "type_disabled"         :true,
        "trac_url"              :"https://gruyere.lps.ufrj.br/trac",
        "xmlrpc_url"            :"/trac/xmlrpc",
        "on_connect"            : function(){
            var json = {};
            //var info = get_user_information();
            //json.user = info.user;
            //json.password = info.password;
            json.ticket_reporter = "{{user.username}}";
            return json;
        }
    });
}

jQuery.fn.createHeader = function() {
    var header = this;
    cssHeader= {
        'width'      : '96.6%',
        'background' : '#000066',
        'color'      : 'white',
        'padding'    : '15px 20px',
        'height'     : '15px',
        'clear'      : 'both'
    }
    cssUserTools ={
        'color'       : '#FFFFCC',
        'font-size'   : '11px',
        'padding'     : '1.2em 10px',
        'position'    : 'relative',
        'right'       : '0',
        'text-align'  : 'right',
        'top'         : '0',
        'font-family' : '"Lucida Grande","DejaVu Sans","Bitstream Vera Sans",Verdana,Arial,sans-serif'
    }
    cssLink = {
        'color': 'white',
        'text-decoration': 'none'
    }
    header.css(cssHeader);
    brand = $('<div></div>');
    brand.attr('id', 'branding');
    header.append(brand);
    ut = $('<div></div>');
    ut.attr('id', 'user-tools');
    usermsg = 'Bem-vindo {{user.username}}! ';
    ut.text(usermsg);
    ut.css(cssUserTools);
    {% if user.is_staff %}
        admLink = $('<a />');
        admLink.attr('href', '{{url}}admin/');
        admLink.text('Administração');
        admLink.css(cssLink);
        ut.append(admLink);
    {% endif %}
    {% if user.is_authenticated %}
    	ut.append(" ");
		logoutLink = $('<a />');
		logoutLink.attr('href', '{{url}}logout/');
		logoutLink.text('Sair');
		logoutLink.css(cssLink);
		ut.append(logoutLink);
    {% endif %}
    header.append(ut);
    $('a', ut).hover(function(){
        $(this).css({
        "text-decoration": "underline"
        });
    }, function(){
        $(this).css({
        "text-decoration": "none"
        });
    });
};

jQuery.fn.createFooter = function() {
    var footer = this;
    ct = $('<div></div>');
    {% if user.is_staff %}
        contactLink = $('<a />');
        contactLink.attr('id', 'trac');
        contactLink.text('Fale Conosco');
        ct.append(contactLink);
        var deps = [
            "{{MEDIA_URL}}js/jquery.fancybox-1.3.4.pack.js",
            "{{MEDIA_URL}}js/rpc.js",
            "{{MEDIA_URL}}js/jquery.tracForm.js"
        ];
        $("<link/>", {
           rel: "stylesheet",
           type: "text/css",
           href: "{{MEDIA_URL}}/css/jquery.fancybox-1.3.4.css"
        }).appendTo("head");
        $("<link/>", {
           rel: "stylesheet",
           type: "text/css",
           href: "{{MEDIA_URL}}/css/jquery.tracForm.css"
        }).appendTo("head");
        jQuery.getScript( deps, setup_tracForm());
    {% endif %}
    footer.append(ct);
    cssObj= {
        'width'     : '96.6%',
        "background": "none repeat scroll 0 0 #000066",
        'color'     : 'white',
        'padding'   : '15px 20px',
        "height"    : "20px",
		"position"  : "fixed",
		"bottom"    : "0px",
    }
    footer.css(cssObj);
    footer.prev().css({'margin-bottom': '20px'});
    footer.before($("<div />").addClass('clear'));
    $('.clear').css({'clear':'both'});
    $('a', footer).css({
        "color": "white",
        "text-decoration": "none"
    });
    $('a', footer).hover(function(){
        $(this).css({
        "text-decoration": "underline"
        });
    }, function(){
        $(this).css({
        "text-decoration": "none"
        });
    });
};

function positionFooter() { 
    var mFoo = $("footer"); 
    if (
        (($(document.body).height() + mFoo.height()) < $(window).height() && mFoo.css("position") == "fixed") ||
        ($(document.body).height() < $(window).height() && mFoo.css("position") != "fixed")
    ) {
        mFoo.css({ position: "fixed", bottom: "0px" }); 
    } else { 
        mFoo.css({ position: "static" }); 
    } 
}
$(document).ready(function () {
    positionFooter();
    $(window).scroll(positionFooter);
    $(window).resize(positionFooter); 
    $(window).load(positionFooter); }
);
