(function($) {

    $.fn.tracForm = function(options){

        //Default values
        $.fn.tracForm.defaults = {
            //Title to "back to the form" link.
            'back_link_title'       :"Back to the form",
            //The difference between html and tracForm folder.
            'base_url'              :"",
            //Close fancybox after the ticket being submitted
            'close_automatically'   :true,
            //Time to wait until fancybox closes
            'closing_time'          :4000,
            //The selected component
            'component'             :"",
            //If the component is disabled
            'component_disabled'    :false,
            //Title when the ticket is being submitted
            'creating_ticket_title' :"Please wait",
            //Message when the ticket is being submitted
            'creating_ticket_message':"Submitting...",
            //If you are debugging or in development version, turn this on.
            'debug'                 :false,
            //The form title to be set when an error occurs.
            'error_title'           :"Error",
            //The message that will be shown to the user when an
            //error occurs
            'error_message'         :'An error has occurred. Please contact: {{email}} ',
            //Contact email
            'email'                 :'',
            //Set the fancybox configuration.
            'fancybox_config'       :{
                                        'autoDimensions':false,
                                        'padding'       :'10',
                                        'width'         :'500',
                                        'height'        :'550'
                                    },
            //CSS object to modify the form.
            'form_css'              :"",
            //Callback when the XMLRPC is being connected.
            'on_connect'            :null,
            //Callback when the form is being installed.
            'on_install'            :null,
            //The priority
            'priority'              :"",
            //If the priority is disabled
            'priority_disabled'     :false,
            //The message that will be shown to the user when the
            //ticket gets submitted.
            'ticket_created_message'  :'Ticket submitted.',
            //The form title when the ticket gets submitted.
            'ticket_created_title':'Thank you for your report',
            //Trac URL
            'trac_url'              :"",
            //The selected type
            'type'                  :"",
            //If the type is disabled
            'type_disabled'         :false,
            //The link to connect with XMLRPC interface on Trac.
            'xmlrpc_url'            :""
        }
        //Extending the options
        var options = get_user_options();

        /* -- Global variables initialization -- */

        //The root element as a jQuery object
        var $root;
        //The form HTML
        var raw_html;
        //The form element as a jQuery object
        var $form;
        //The container element as a jQuery object
        var $container;
        //The XMLRPC service
        var service;
        //Valid Trac components
        var components;
        //If the ajax request in completed
        var components_added = false;
        //Valid Trac types
        var types;
        //If the ajax request in completed
        var types_added = false;
        //Valid Trac priorities
        var priorities;
        //If the ajax request in completed
        var priorities_added = false;
        //Ticket reporter
        var ticket_reporter;
        //Ticket reporter email
        var ticket_reporter_email;

        /* --------------------------- */

        /* ----------- Functions ------------ */

        //This function is responsible for extend the options
        //and replace the variables
        function get_user_options() {
            //Extend the object
            var o = $.extend( $.fn.tracForm.defaults , options );
            //Do the email tag
            o.email = '<a href="mailto:' + o.email + '" >'+ o.email + '</a>';
            //For each option, replace the variable if it is a string
            $.each( o , function( key , value ){
                if (  typeof( value ) == "string" )
                    o[ key ] = replace_variables( value , o );
            });

            return o;
        }
        //This function is responsible for replace the variables
        function replace_variables( value , _options ) {
            if ( _options )
                var options = _options;
            //Global pattern to discover variables in a string
            var var_patt = /{{([^\}\{]*)\}}/g;
            var result = var_patt.exec( value );
            if ( result ) {
                var result_str = result[0];
                var index = result_str.replace( "{{" , "" ).replace( "}}" , "" );
                if ( options[ index ] )
                    value = value.replace( result_str , options[ index ] );
            }
            return value;
        }
        //This function is responsible for:
        //1. Add the form HTML to the page.
        //2. Render the page with the correct CSS
        function install_trac_form() {

            //Get the form HTML and append it to the body
            $.ajax({
                url: options.base_url + '/config/trac_form.html',
                async: false,
                dataType: 'text',
                success: function( html ) {
                    //Get the file content as a jQuery object
                    var $html = $( html );
                    raw_html = html;
                    //Get the form
                    $form = $( "#tracForm_ticket_form" , $html );
                    //Get the container
                    $container = $( "#tracForm_container" , $html );
                    //Append the HTML to the body
                    var $exist_container = $( "#tracForm_container" );
                    if ( $exist_container.length )
                        $exist_container.replaceWith( $container );
                    else
                        $( 'body' ).append( $html );
                    //Set the href, otherwise fancybox won't work
                    $root.attr( 'href' , '#tracForm_container' );
                    //Add types to the form
                    add_types();
                    //Add components to the form
                    add_components();
                    //Add priorities to the form
                    add_priorities();
                },
                complete: function() {
                    //Set the ticket reporter
                    $( "#tracForm_ticket_reporter" , $form ).val( ticket_reporter );
                    //If the user wants to change the CSS
                    if ( options.form_css )
                        $container.css( options.form_css );

                }
            });

            //Callback function
            execute_on_install();

        }
        //This function will be executed after the ajax requests
        function execute_on_install(){
            //If the requests are completed
            if ( components_added && types_added && priorities_added ) {
                //If we have a call back function
                if ( options.on_install ) {
                    //Check if it is valid and execute it
                    if ( $.isFunction( options.on_install ) ) {
                        options.on_install.call( this );
                    } else {
                        throw "Install callback is not a function";
                    }
                }
                //Call fancybox to show the form only when the form
                //contains all the information
                $root.fancybox( options.fancybox_config );

            //If they are not, call the function again
            } else {
                setTimeout( execute_on_install , 20 );
            }
        }
        //This function is responsible for add the right components
        function add_components() {
            if ( components == undefined )
                //Call the Trac to get the components
                service.ticket.component.getAll({
                    params:[],
                    onSuccess:function( _components ){
                        components = _components;
                        fill_selectbox( $( '#tracForm_ticket_component' , $form ) , components );
                    },
                    onException:function( error ){
                        show_message( options.error_title , options.error_message , true );
                        $.fancybox.resize();
                        throw( error );
                    },
                    onComplete:function( response_obj ){
                        components_added = true;
                        if ( options.component || options.component_disabled )
                            focus_value( "#tracForm_ticket_component" , options.component , options.component_disabled );
                    }
                });
            else {
                fill_selectbox( $( '#tracForm_ticket_component' , $form ) , components );
                focus_value( "#tracForm_ticket_component" , options.component , options.component_disabled );
            }
        }
        //This function is responsible for add the right tickets types
        function add_types() {
            if ( types == undefined )
                service.ticket.type.getAll({
                //Call the Trac to get the types
                    params:[],
                    onSuccess:function( _types ){
                        types = _types;
                        fill_selectbox( $( '#tracForm_ticket_type' , $form ) , types );
                    },
                    onException:function( error ){
                        show_message( options.error_title , options.error_message , true );
                        $.fancybox.resize();
                        throw( error );
                    },
                    onComplete:function( response_obj ){
                        types_added = true;
                        if ( options.type || options.type_disabled )
                            focus_value( "#tracForm_ticket_type" , options.type , options.type_disabled );
                    }
                });
            else {
                fill_selectbox( $( '#tracForm_ticket_type' , $form ) , types );
                focus_value( "#tracForm_ticket_type" , options.type , options.type_disabled );
            }
        }
        //This function is responsible for add the right priorities
        function add_priorities() {
            if ( priorities == undefined )
                //Call the Trac to get the priorities
                service.ticket.priority.getAll({
                    params:[],
                    onSuccess:function( _priorities ){
                        priorities = _priorities;
                        fill_selectbox( $( '#tracForm_ticket_priority' , $form ) , priorities );
                    },
                    onException:function( error ){
                        show_message( options.error_title , options.error_message , true );
                        $.fancybox.resize();
                        throw( error );
                    },
                    onComplete:function( response_obj ){
                        priorities_added = true;
                        if ( options.priority || options.priority_disabled )
                            focus_value( "#tracForm_ticket_priority" , options.priority , options.priority_disabled );
                    }
                });
            else {
                fill_selectbox( $( '#tracForm_ticket_priority' , $form ) , priorities );
                focus_value( "#tracForm_ticket_priority" , options.priority , options.priority_disabled );
            }
        }
        //This function is responsible for form validation
        function is_valid(){

            var summary_value = $( "#tracForm_ticket_summary" ).val();
            var reporter_value = $( "#tracForm_ticket_reporter" ).val();
            var component_value = $( "#tracForm_ticket_component" ).val();
            if ( summary_value && reporter_value && component_value )
                return true;

            //If the mandatory fields are empty, do not submit
            //And show a message
            if ( ! summary_value ) show_required_message( "#tracForm_ticket_summary" );
            if ( ! reporter_value ) show_required_message( "#tracForm_ticket_reporter" );
            if ( ! component_value ) show_required_message( "#tracForm_ticket_component" );

            return false;
        }
        //Auxiliar function to show the required message in the form
        function show_required_message ( element_id ){
            //Create the div element
            var $message = $( "<div class='tracForm_required'>" );
            //Create the label element
            var $label = $( "<label>" ).text( "This field is required" );
            //Append the label to the div
            $message.append( $label );
            //Add the div to the element
            $( element_id ).after( $message );
        }
        //Auxiliar function to fill the information in a selectbox
        function fill_selectbox( $select , options ) {
            for ( var i = 0 ; i < options.length ; i++ ) {
                var curr_option = options[ i ];
                var $option = $("<option>").val( curr_option ).html( curr_option );
                $select.append($option);
            }
        }
        //This function is responsible for show any message
        /*
         * You have 3 configuration options:
         * 1. new_title: is the form new title.
         * 2. message: the message you want to show.
         * 3. if you want or not show the back link
         * 4. Data to replace variables
        */
        function show_message( new_title , message , show_back_link , data ){
            //Global pattern to discover variables in a string
            var var_patt = /{{([^\}\{]*)\}}/g;
            //Set the message with the data
            var result = var_patt.exec( message );
            if ( result ) {
                var result_str = result[ 0 ];
                var index = result[ 1 ];
                if ( data[ index ] )
                    message = message.replace( result_str , data[ index ] );
            }
            //Set the new title
            $( "p" , "#tracForm_tracFormTitle" ).replaceWith( html_message( new_title ) );
            //Replace the form by the message
            $form.html( html_message( message ) );
            //Show the link to show the original form again if the option is
            //set and if there is no back link
            if ( show_back_link && ( $( "#tracForm_back_link" ).length == 0 ) ){
                var $back_link = $( "<p><a href='#' id='tracForm_back_link'>" + options.back_link_title + "</a></p>" );
                $form.after( $back_link );
            }
        }
        //Wrap the message into <p> tags
        function html_message( message ){
            var html = "";
            var lines = message.split( "\n" );
            if ( lines )
                for ( var i = 0 ; i < lines.length ; i++ )
                    html += "<p>" + lines[ i ] + "</p>";
            else
                html = "<p>" + message + "</p>";
            return html;
        }
        //Focus a value in a selectbox
        //You can specify if it is disabled or not
        function focus_value( element_id , value , disabled ){
            var $element = $( element_id );
            $( "option" , $element ).each( function(){
                var $option = $( this );
                if ( $option.text() == value )
                    $option.attr( "selected" , true );
            });
            if ( disabled )
                $element.attr( "disabled" , disabled );
        }
        function main() {

            //Call the on_connect callback function
            if ( $.isFunction( options.on_connect ) ) {

                //Set the xmlrpc options
                var xmlrpc_options =
                {
                    asynchronous: true,
                    user        : "",
                    password    : "",
                    //Since JSON-RPC does not work properly
                    //with Trac, XML-RPC was chosen.
                    protocol    : "XML-RPC",
                    //Choose the methods. It is faster than list methods.
                    methods     : [ 
                                    "ticket.type.getAll" ,
                                    "ticket.component.getAll" ,
                                    "ticket.priority.getAll" ,
                                    "ticket.create" ,
                                    "system.getAPIVersion"
                                ]
                };
                //Get the json returned
                var _options = options.on_connect();
                //Fill the xmlrpc options with it
                if ( _options.user == undefined ) _options.user = "";
                if ( _options.password == undefined ) _options.password = "";
                xmlrpc_options.user = _options.user;
                xmlrpc_options.password = _options.password;
                //And set the ticket reporter
                if ( _options.ticket_reporter == undefined )
                    _options.ticket_reporter = "";
                ticket_reporter = _options.ticket_reporter;
                //Set the reporter email
                if ( _options.ticket_reporter_email == undefined )
                    _options.ticket_reporter_email = "";
                ticket_reporter_email = _options.ticket_reporter_email;
                //Connect to Trac
                service = new rpc.ServiceProxy( options.xmlrpc_url , xmlrpc_options );
            } else {
                throw "Connect callback is not a function";
            }
            //Install the form
            install_trac_form();

        }


        /* --------------------------- */

        return this.each(function(){

            /* -- Install the plugin -- */

            //Get the root element
            $root = $( this );

            //Execute the main actions
            main();

            /* ---------------------------- */

            /* ------- Actions ------- */

            //If the user click on the back button
            $( "#tracForm_back_link" ).live( 'click', function(){
                //Reinstall the form
                install_trac_form();
                //Remove the link
                $( this ).remove();
            });

            //If the user click on the submit button
            $( '#tracForm_ticket_submit_button' ).live( 'click' , function(){

                //Check if the form is valid and if it is not, 
                //don't let user submit it showing the errors
                if ( ! is_valid() ) return false;

                //Get the summary and description
                var ticket_summary = $( '#tracForm_ticket_summary' ).val();
                var ticket_description = $( '#tracForm_ticket_description' ).val() ;

                //Variable to send to Trac as parameter of create_ticket function
                var ticket_attr = {
                    component   : $( "#tracForm_ticket_component" , $form ).val(),
                    type        : $( "#tracForm_ticket_type" , $form ).val(),
                    reporter    : $( "#tracForm_ticket_reporter" ).val(),
                    priority    : $( "#tracForm_ticket_priority" , $form ).val(),
                    cc          : ticket_reporter_email
                };

                //If we are debugging it, only show the information
                if ( options.debug ){

                    service.system.getAPIVersion({
                        params: [],
                        onSuccess:function( api_version ){
                            var debug_message = "";
                            debug_message += html_message( "Main link id: " + $root.attr( 'id' ) );
                            debug_message += html_message( "Ticket summary: " + ticket_summary );
                            debug_message += html_message( "Ticket description: " + ticket_description );
                            debug_message += html_message( "Ticket reporter: " + ticket_reporter );
                            debug_message += html_message( "Components: " + components );
                            debug_message += html_message( "Selected component: " + ticket_attr.component );
                            debug_message += html_message( "Types: " + types );
                            debug_message += html_message( "Selected type: " + ticket_attr.type );
                            debug_message += html_message( "Priorities: " + priorities );
                            debug_message += html_message( "Selected priority: " + ticket_attr.priority );
                            debug_message += html_message( "XMLRPC API version: " + api_version );
                            show_message( "Debug Information" , debug_message , true );
                            $.fancybox.resize();
                        },
                        onException:function( error ){
                            show_message( options.error_title , options.error_message , true );
                            $.fancybox.resize();
                            throw( error );
                        },
                        onComplete:function(responseObj){
                        }
                    });

                //But if we are not, submit the ticket
                } else {
                    show_message( options.creating_ticket_title , options.creating_ticket_message , false );
                    //Call the service to create the ticket
                    service.ticket.create({
                        params: [ ticket_summary , ticket_description , ticket_attr ],
                        onSuccess:function( ticket_id ){
                            var data = {};
                            data.ticket_id = ticket_id;
                            show_message( options.ticket_created_title , options.ticket_created_message , true , data);
                            $.fancybox.resize();
                            if ( options.close_automatically )
                                setTimeout( function() {
                                                $.fancybox.close();
                                            },
                                        options.closing_time );
                        },
                        onException:function( error ){
                            show_message( options.error_title , options.error_message , true );
                            $.fancybox.resize();
                            throw( error );
                        },
                        onComplete:function(responseObj){
                        }
                    });
                }

            });

            /* ---------------------------- */

        });

    };

}) (jQuery);
