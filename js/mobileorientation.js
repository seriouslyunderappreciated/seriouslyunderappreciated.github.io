// Store the meta element
var viewport_meta = document.getElementById('viewport-meta');

// Define our viewport meta values
var viewports = {
		default: viewport_meta.getAttribute('content'),
		landscape: 'initial-scale=1'
	};

// Change the viewport value based on screen.width
var viewport_set = function() {
		if ( window.orientation == 0 || window.orientation == 180 )
			viewport_meta.setAttribute( 'content', viewports.landscape );
		else
			viewport_meta.setAttribute( 'content', viewports.default );
	}

// Set the correct viewport value on page load
viewport_set();

// Set the correct viewport after device orientation change or resize
window.onresize = function() { 
	viewport_set(); 
}