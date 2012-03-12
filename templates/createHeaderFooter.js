jQuery.fn.createHeader = function() {
    var header = this;
    cssObj= {
        'width': '96.6%',
        'background':   '#000066',
        'color':          'white',
        'padding':    '15px 20px',
        'height':    '15px',
        'clear': 'both',
    }
    header.css(cssObj);
    brand = $('<div></div>');
    brand.attr('id', 'branding');
    header.append(brand);
    ut = $('<div></div>');
    ut.attr('id', 'user-tools');
    usermsg = 'Bem-vindo {{user.username}}! ';
    ut.text(usermsg);
    {% if user.is_staff %}
        admLink = $('<a />');
        admLink.attr('href', '{{url}}admin/');
        admLink.text('Administração ');
        ut.append(admLink);
    {% endif %}
    logoutLink = $('<a />');
    logoutLink.attr('href', '{{url}}logout/');
    logoutLink.text('Sair');
    ut.append(logoutLink);
    header.append(ut);
};

jQuery.fn.createFooter = function() {
    var footer = this;
    ct = $('<div></div>');
    {% if user.is_staff %}
        contactLink = $('<a />');
        contactLink.attr('href', '{{url}}contact/');
        contactLink.text('Fale Conosco');
        ct.append(contactLink);
    {% endif %}
    footer.append(ct);
    cssObj= {
        'width': '96.6%',
		"background": "none repeat scroll 0 0 #000066",
        'color':          'white',
        'padding':    '15px 20px',
        'clear': 'both',
		 "position":"fixed",
		"bottom": "0px",
		"height" : "20px",
    }
    footer.css(cssObj);
    footer.prev().css({'margin-bottom': '20px'});
    footer.before($("<div />")
        .addClass('clear')
    );
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
