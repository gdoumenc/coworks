jQuery(function ($) {
	"use strict";

	// Headhesive
	var options = {
			offset: 600,
			classes: {
			clone:   'banner--clone',
			stick:   'banner--stick',
			unstick: 'banner--unstick'
		}
	};

	// Initialise with options
	var banner = new Headhesive('.navbar', options);

	$('body').on('click', 'a[href="#"]', function(event) {
		return false;
	});

	// Add padding to parent on mobile devices
	$('.grey-background').parent().addClass('mobile-padding');

	// Fake loading
	$("#fakeLoader").fakeLoader({
		spinner:"spinner1",
		bgColor:"#1b1d1e"
	});

	// Bootstrap carousel
	$('.bs-carousel').carousel({
		interval: 10000,
		pause: "hover"
	});

	// Tabs
	$('.tabs').tabs();

	// Number counter
	$('.counter span').counterUp({
		delay: 10,
		time: 500
	});

	// Toggle class for burger menu
	$('.navbar-header').on('click', '.navbar-toggle', function(event) {
		$(this).toggleClass('minimize');
		$('body').toggleClass('open');
	});

	// Owl carousel
	$(window).on('load resize scroll', function(){  
		$("#partners").owlCarousel({
			loop: true,
			autoplay: true,
			autoplayTimeout: 4000,
			autoplaySpeed: 500,
			autoplayHoverPause: true,
			responsive : {
				480 : { items : 1  },
				768 : { items : 3  },
				1024 : { items : 4 }
			},
		});  
		
		$(".owl-carousel").owlCarousel({
			items: 1,
			loop: true,
			autoplay: true,
			autoplayTimeout: 4000,
			autoplaySpeed: 500,
			autoplayHoverPause: true,
			responsive : {
				480 : { items : 1  },
				768 : { items : 2  },
				1024 : { items : 3 }
			},
		});
	});

	// History timeline left / right floats
	$('.history article:not(.clear):odd').addClass('left');
	$('.history article:not(.clear):even').addClass('right');

	// Wrap all select types
	$('select').wrap('<div class="select-wrapper" />')

	// Vertical aloign navbar
	var $nav = $('.nav').height();
	$('.nav').css('margin-top', - $nav / 2 );

	// Hero slide dynamic sizing
	$(window).on('load resize scroll', function(){

		var $heading = $('.wrapper .heading').outerHeight();
		var $navbar = $('.wrapper .navbar-header').outerHeight();
		$('#hero .item, #hero.single-page .blurb, #hero.error-page .container').css('padding-top', $heading + $navbar );

		var $window = $(window).height();
		$('#hero').css('height', window.innerHeight - 75);
		$('#hero.error-page').css('height', window.innerHeight);

	});


	// Match hweight of elements
	$(window).on('load', function(){
		$('.matchHeight').matchHeight();
		$('.icon-grid, .product-wrapper').matchHeight({
			byRow: true
		});
	});

	// Create revealing footer
	var $footer = $('footer').outerHeight();
	$('.wrapper').css('padding-bottom', $footer);

	// Change SVG colour
	jQuery('img.svg').each(function(){
		var $img = jQuery(this);
		var imgID = $img.attr('id');
		var imgClass = $img.attr('class');
		var imgURL = $img.attr('src');

		jQuery.get(imgURL, function(data) {
			// Get the SVG tag, ignore the rest
			var $svg = jQuery(data).find('svg');

			// Add replaced image's ID to the new SVG
			if(typeof imgID !== 'undefined') {
				$svg = $svg.attr('id', imgID);
			}
			// Add replaced image's classes to the new SVG
			if(typeof imgClass !== 'undefined') {
				$svg = $svg.attr('class', imgClass+' replaced-svg');
			}

			// Remove any invalid XML tags as per http://validator.w3.org
			$svg = $svg.removeAttr('xmlns:a');

			// Replace image with new SVG
			$img.replaceWith($svg);

		}, 'xml');

	});

	// Wicked credit to
	// http://www.zachstronaut.com/posts/2009/01/18/jquery-smooth-scroll-bugs.html
	var scrollElement = 'html, body';
	$('html, body').each(function () {
		var initScrollTop = $(this).attr('scrollTop');
		$(this).attr('scrollTop', initScrollTop + 1);
		if ($(this).attr('scrollTop') === initScrollTop + 1) {
			scrollElement = this.nodeName.toLowerCase();
			$(this).attr('scrollTop', initScrollTop);
			return false;
		}    
	});
	
	// Smooth scrolling for internal links
	$("a[href^='#']").not('.tabs a, a.carousel-control, .show-more').click(function(event) {
		event.preventDefault();
		
		var $this = $(this),
		target = this.hash,
		$target = $(target);
		
		$(scrollElement).stop().animate({
			'scrollTop': $target.offset().top
		}, 1500, 'swing', function() {
			window.location.hash = target;
		});
		
	});

	// Google maps
	if ($("#map").length > 0){
		
			$("#map").gmap3({                        
			map:{
				options:{
					zoom: 14,
					center: new google.maps.LatLng(51.513614, -0.136549),
					mapTypeId: google.maps.MapTypeId.ROADMAP,
					mapTypeControlOptions: {
						mapTypeIds: [google.maps.MapTypeId.ROADMAP, "style1"]
					},
					styles:
						[
							{
								"featureType": "all",
								"elementType": "labels.text.fill",
								"stylers": [
									{
										"saturation": "0"
									},
									{
										"color": "#454a4e"
									},
									{
										"lightness": "0"
									}
								]
							},
							{
								"featureType": "all",
								"elementType": "labels.text.stroke",
								"stylers": [
									{
										"visibility": "on"
									},
									{
										"color": "#1b1d1e"
									},
									{
										"lightness": "0"
									}
								]
							},
							{
								"featureType": "all",
								"elementType": "labels.icon",
								"stylers": [
									{
										"visibility": "off"
									}
								]
							},
							{
								"featureType": "administrative",
								"elementType": "geometry.fill",
								"stylers": [
									{
										"color": "#000000"
									},
									{
										"lightness": 20
									}
								]
							},
							{
								"featureType": "administrative",
								"elementType": "geometry.stroke",
								"stylers": [
									{
										"color": "#000000"
									},
									{
										"lightness": 17
									},
									{
										"weight": 1.2
									}
								]
							},
							{
								"featureType": "administrative",
								"elementType": "labels.text.fill",
								"stylers": [
									{
										"visibility": "on"
									},
									{
										"color": "#cbb27c"
									}
								]
							},
							{
								"featureType": "landscape",
								"elementType": "all",
								"stylers": [
									{
										"visibility": "on"
									}
								]
							},
							{
								"featureType": "landscape",
								"elementType": "geometry",
								"stylers": [
									{
										"color": "#1b1d1e"
									},
									{
										"lightness": "0"
									}
								]
							},
							{
								"featureType": "poi",
								"elementType": "geometry",
								"stylers": [
									{
										"color": "#1b1d1e"
									},
									{
										"lightness": "-2"
									},
									{
										"gamma": "1"
									}
								]
							},
							{
								"featureType": "road.highway",
								"elementType": "geometry.fill",
								"stylers": [
									{
										"color": "#1b1d1e"
									},
									{
										"lightness": "5"
									}
								]
							},
							{
								"featureType": "road.highway",
								"elementType": "geometry.stroke",
								"stylers": [
									{
										"color": "#1b1d1e"
									},
									{
										"lightness": 29
									},
									{
										"weight": 0.2
									},
									{
										"visibility": "off"
									}
								]
							},
							{
								"featureType": "road.arterial",
								"elementType": "geometry",
								"stylers": [
									{
										"color": "#1b1d1e"
									},
									{
										"lightness": "5"
									}
								]
							},
							{
								"featureType": "road.local",
								"elementType": "geometry",
								"stylers": [
									{
										"color": "#1b1d1e"
									},
									{
										"lightness": "5"
									}
								]
							},
							{
								"featureType": "transit",
								"elementType": "geometry",
								"stylers": [
									{
										"color": "#1b1d1e"
									},
									{
										"lightness": "12"
									}
								]
							},
							{
								"featureType": "water",
								"elementType": "geometry",
								"stylers": [
									{
										"color": "#1b1d1e"
									},
									{
										"lightness": "3"
									}
								]
							}
						],
					disableDefaultUI: true,
					draggable: true,
					scrollwheel: false,
				}
			}            
			,
			marker:{
				latLng:[51.513614, -0.136549],
				options:{
					icon: new google.maps.MarkerImage("images/pin.png", new google.maps.Size(74, 97, "px", "px")),
				}
			}

		});

	}

});