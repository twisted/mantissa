/**
 * Copyright (c) 2006, Bill W. Scott
 * All rights reserved.
 *
 * This work is licensed under the Creative Commons Attribution 2.5 License. To view a copy 
 * of this license, visit http://creativecommons.org/licenses/by/2.5/ or send a letter to 
 * Creative Commons, 543 Howard Street, 5th Floor, San Francisco, California, 94105, USA.
 *
 * This work was created by Bill Scott (billwscott.com, looksgoodworkswell.com).
 * 
 * The only attribution I require is to keep this notice of copyright & license 
 * in this original source file.
 */
YAHOO.namespace("extension");

YAHOO.extension.Carousel = function(carouselElementID, carouselCfg) {
 		this.init(carouselElementID, carouselCfg);
	};

YAHOO.extension.Carousel.prototype = {

	
	init: function(carouselElementID, carouselCfg) {

 		this.carouselElemID = carouselElementID;
 		this.carouselElem = YAHOO.util.Dom.get(carouselElementID);
 		//YAHOO.util.Dom.setStyle(this.carouselElem, "visibility", "hidden")

 		this.start = 1;
 		this.prevEnabled = true;
 		this.nextEnabled = true;
 		
 		// Create the config object
 		this.cfg = new YAHOO.util.Config(this);

		this.cfg.addProperty("numVisible", { 
				value:3, 
				suppressEvent:true
		} );
		this.cfg.addProperty("animationSpeed", { 
				value:.25, 
				suppressEvent:true
		} );
		this.cfg.addProperty("animationMethod", { 
				value:  YAHOO.util.Easing.easeOut, 
				suppressEvent:true
		} );
		this.cfg.addProperty("scrollInc", { 
				value:3, 
				suppressEvent:true
		} );
		this.cfg.addProperty("size", { 
				value:1000000, 
				suppressEvent:true
		} );
		this.cfg.addProperty("orientation", { 
				value:"horizontal", 
				suppressEvent:true
		} );
		this.cfg.addProperty("navMargin", { 
				value:0, 
				suppressEvent:true
		} );
		this.cfg.addProperty("loadInitHandler", { 
				value:null, 
				suppressEvent:true
		} );
		this.cfg.addProperty("prevElementID", { 
				value:null, 
				suppressEvent:true
		} );
		this.cfg.addProperty("nextElementID", { 
				value:null, 
				suppressEvent:true
		} );
		this.cfg.addProperty("loadNextHandler", { 
				value:null, 
				suppressEvent:true
		} );
		this.cfg.addProperty("loadPrevHandler", { 
				value:null, 
				suppressEvent:true
		} );
		this.cfg.addProperty("prevButtonStateHandler", { 
				value:null, 
				suppressEvent:true
		} );
		this.cfg.addProperty("nextButtonStateHandler", { 
				value:null, 
				suppressEvent:true
		} );
		this.cfg.addProperty("autoPlay", { 
				value:0, 
				suppressEvent:true
		} );
		this.cfg.addProperty("wrap", { 
				value:false, 
				suppressEvent:true
		} );
		
 		if(carouselCfg) {
 			this.cfg.applyConfig(carouselCfg);
 		}
 		
 		this.numVisible = this.cfg.getProperty("numVisible");
 		this.scrollInc = this.cfg.getProperty("scrollInc");
		this.navMargin = this.cfg.getProperty("navMargin");
 		this.animSpeed = this.cfg.getProperty("animationSpeed");
		this.initHandler = this.cfg.getProperty("loadInitHandler");
		this.size = this.cfg.getProperty("size");
		this.wrap = this.cfg.getProperty("wrap");
		this.animationMethod = this.cfg.getProperty("animationMethod");
		this.orientation = this.cfg.getProperty("orientation");
		this.nextElementID = this.cfg.getProperty("nextElementID");
		this.prevElementID = this.cfg.getProperty("prevElementID");
		this.autoPlay = this.cfg.getProperty("autoPlay");
		this.autoPlayTimer = null;
		
 		var carouselListClass = "carousel-list";
 		var carouselClipRegionClass = "carousel-clip-region";
 		var carouselNextClass = "carousel-next";
 		var carouselPrevClass = "carousel-prev";
 		
 		this.carouselList = YAHOO.util.Dom.getElementsByClassName(carouselListClass, 
												"ul", this.carouselElem)[0];
		/*if(this.isVertical()) {
			YAHOO.util.Dom.setStyle(this.carouselList, "height", "10000000px");									
		} else {
			YAHOO.util.Dom.setStyle(this.carouselList, "width", "10000000px");									
		}*/
		
		if(this.nextElementID == null) {
			this.carouselNext = YAHOO.util.Dom.getElementsByClassName(carouselNextClass, 
												"div", this.carouselElem)[0];
		} else {
			this.carouselNext = YAHOO.util.Dom.get(this.nextElementID);
		}

		if(this.nextElementID == null) {
 			this.carouselPrev = YAHOO.util.Dom.getElementsByClassName(carouselPrevClass, 
												"div", this.carouselElem)[0];
		} else {
			this.carouselPrev = YAHOO.util.Dom.get(this.prevElementID);
		}
		
		this.clipReg = YAHOO.util.Dom.getElementsByClassName(carouselClipRegionClass, 
												"div", this.carouselElem)[0];
												
		
		if(this.isVertical()) {
			YAHOO.util.Dom.addClass(this.carouselList, "carousel-vertical");
		}
		 		
 		this.scrollNextAnim = new YAHOO.util.Motion(this.carouselList, this.scrollNextParams, 
   								this.animSpeed, this.animationMethod);
 		this.scrollPrevAnim = new YAHOO.util.Motion(this.carouselList, this.scrollPrevParams, 
   								this.animSpeed, this.animationMethod);
		if(this.isValidObj(this.carouselNext)) {
			YAHOO.util.Event.addListener(this.carouselNext, "click", this._scrollNext, this);
		} 
		
		if(this.isValidObj(this.carouselPrev)) {
			YAHOO.util.Event.addListener(this.carouselPrev, "click", this._scrollPrev, this);
		}
		
		// --- Event Handling
		
		// for now wire up handlers in our class... 
		// this will wire to handlers passed into config
		if(this.isValidObj(this.initHandler)) {
			this.loadInitialEvt = new YAHOO.util.CustomEvent("onLoadInit", this);
			this.loadInitialEvt.subscribe(this.initHandler, this);
		}
		this.nextHandler = this.cfg.getProperty("loadNextHandler");
		if(this.isValidObj(this.nextHandler)) {
			this.loadNextEvt = new YAHOO.util.CustomEvent("onLoadNext", this);
			this.loadNextEvt.subscribe(this.nextHandler, this);
		}
		this.prevHandler = this.cfg.getProperty("loadPrevHandler");
		if(this.isValidObj(this.prevHandler)) {
			this.loadPrevEvt = new YAHOO.util.CustomEvent("onLoadPrev", this);
			this.loadPrevEvt.subscribe(this.prevHandler, this);
		}
		this.prevButtonStateHandler = this.cfg.getProperty("prevButtonStateHandler");
		if(this.isValidObj(this.prevButtonStateHandler)) {
			this.prevButtonStateEvt = new YAHOO.util.CustomEvent("onPrevButtonStateChange", 
							this);
			this.prevButtonStateEvt.subscribe(this.prevButtonStateHandler, this);
		}
		this.nextButtonStateHandler = this.cfg.getProperty("nextButtonStateHandler");
		if(this.isValidObj(this.nextButtonStateHandler)) {
			this.nextButtonStateEvt = new YAHOO.util.CustomEvent("onNextButtonStateChange", this);
			this.nextButtonStateEvt.subscribe(this.nextButtonStateHandler, this);
		}
		
  		YAHOO.util.Event.onAvailable(this.carouselElemID + "-item-1", this.firstElementIsLoaded, this);  		
		this.loadInitial();	
	},

	addItem: function(idx, innerHTML) {
 		var liElem = this.getCarouselItem(idx);

	    // does not exist, create it
	    if(!this.isValidObj(liElem)) {
	    	liElem = document.createElement("li");
			liElem.id = this.carouselElemID + "-item-" + idx;
			liElem.innerHTML = innerHTML;
			this.carouselList.appendChild(liElem);
			
			// OK, this should not be needed. But without setting this explicitly
			// vertical scroll will drift (by some fraction of a pixel) ! :-/
			if(this.isVertical()) {
				YAHOO.util.Dom.setStyle(liElem, "height", liElem.offsetHeight + "px");
				//YAHOO.util.Dom.setStyle(liElem, "width", liElem.offsetWidth + "px");
			}
		}
	},

	firstElementIsLoaded: function(me) {
 		var ulKids = me.carouselList.childNodes;
 		var li = null;
		for(var i=0; i<ulKids.length; i++) {
		
			li = ulKids[i];
			if(li.tagName == "LI" || li.tagName == "li") {
				break;
			}
		}
		if(me.isVertical()) {
			var liPaddingWidth = parseInt(YAHOO.util.Dom.getStyle(li, "paddingLeft")) + 
						parseInt(YAHOO.util.Dom.getStyle(li, "paddingRight")) + 
						parseInt(YAHOO.util.Dom.getStyle(li, "marginLeft")) + 
						parseInt(YAHOO.util.Dom.getStyle(li, "marginRight"));
			var liPaddingHeight = parseInt(YAHOO.util.Dom.getStyle(li, "paddingTop")) + 
						parseInt(YAHOO.util.Dom.getStyle(li, "paddingBottom")) + 
						parseInt(YAHOO.util.Dom.getStyle(li, "marginTop")) + 
						parseInt(YAHOO.util.Dom.getStyle(li, "marginBottom"));
			
			me.scrollAmountPerInc = (li.offsetHeight+liPaddingHeight);
			me.clipReg.style.width = (li.offsetWidth + liPaddingWidth) + "px";
			me.clipReg.style.height = (me.scrollAmountPerInc*me.numVisible) + "px";
			me.carouselElem.style.width = (li.offsetWidth + liPaddingWidth*2) + "px";
		} else {
			var liPaddingWidth = parseInt(YAHOO.util.Dom.getStyle(li, "paddingLeft")) + 
						parseInt(YAHOO.util.Dom.getStyle(li, "paddingRight")) + 
						parseInt(YAHOO.util.Dom.getStyle(li, "marginLeft")) + 
						parseInt(YAHOO.util.Dom.getStyle(li, "marginRight"));
						
			me.scrollAmountPerInc = (li.offsetWidth+liPaddingWidth);
			me.carouselElem.style.width = ((me.scrollAmountPerInc*me.numVisible)+me.navMargin*2) + "px";
			me.clipReg.style.width = (me.scrollAmountPerInc*me.numVisible)+"px";
		}
		
		YAHOO.util.Dom.setStyle(me.carouselElem, "visibility", "visible");
	},
	
	scrollNext: function() {
		this._scrollNext(null, this);
		
		// we know the timer has expired.
		this.autoPlayTimer = null;
		if(this.autoPlay != 0) {
			this.autoPlayTimer = this.startAutoPlay();
		}
	},
	
	startAutoPlay: function(interval) {
		// if interval is passed as arg, then set autoPlay to this interval.
		if(this.isValidObj(interval)) {
			this.autoPlay = interval;
		}
		
		// if we already are playing, then do nothing.
		if(this.autoPlayTimer !== null) {
			return this.autoPlayTimer;
		}
				
		var oThis = this;  
		var autoScroll = function() { oThis.scrollNext(); };
		var timeoutId = setTimeout( autoScroll, this.autoPlay );
		return timeoutId;
	},

	stopAutoPlay: function() {
		if (this.autoPlayTimer !== null) {
			clearTimeout(this.autoPlayTimer);
			this.autoPlayTimer = null;
		}
	},
	
	scrollPrev: function() {
		this._scrollPrev(null, this);
	},
	
	// scroll to new start with animation
	scrollTo: function(newStart) {
		this.position(newStart, true);
	},
	
	
	// move to start, no animation.
	moveTo: function(newStart) {
		this.position(newStart, false);
	},
	
	position: function(newStart, showAnimation) {
		// do we bypass the isAnimated check?
		if(newStart > this.start) {
			var inc = newStart - this.start;
			this._scrollNextInc(this, inc, showAnimation);
		} else {
			var dec = this.start - newStart;
			this._scrollPrevInc(this, dec, showAnimation);
		}
	},
	
	
	// event handler
	_scrollNext: function(e, carousel) {
		if(carousel.scrollNextAnim.isAnimated()) {
			return false; // might be better to set ourself waiting for animation completion and
			// then just do this function. that will allow faster scroll responses.
		}

		// if fired by an event and wrap is set and we are already at end then wrap
		var currEnd = carousel.start + carousel.numVisible-1;
		if(carousel.wrap && currEnd == carousel.size) {
			var currAnimSpeed = carousel.animSpeed;
			carousel.scrollTo(1);
		} else if(e !== null) { // event fired this so disable autoplay
			carousel.stopAutoPlay();
			carousel._scrollNextInc(carousel, carousel.scrollInc, (carousel.animSpeed != 0));
		} else {
			carousel._scrollNextInc(carousel, carousel.scrollInc, (carousel.animSpeed != 0));
		}
		

	},
	
	// probably no longer need carousel passed in, this should be correct now.
	_scrollNextInc: function(carousel, inc, showAnimation) {

		var newEnd = carousel.start + inc + carousel.numVisible - 1;
		newEnd = (newEnd > carousel.size) ? carousel.size : newEnd;
		var newStart = newEnd - carousel.numVisible + 1;
		inc = newStart - carousel.start;
		carousel.start = newStart;

		// if the prev button is disabled and start is now past 1, then enable it
		if((carousel.prevEnabled == false) && (carousel.start > 1)) {
			carousel.enablePrev();
		}
		// if next is enabled && we are now at the end, then disable
		if((carousel.nextEnabled == true) && (newEnd == carousel.size)) {
			carousel.disableNext();
		}
		
		if(inc > 0) {
			if(carousel.isValidObj(carousel.nextHandler)) {
				var first = carousel.start;
				var last = 	carousel.start + carousel.numVisible - 1;
				var alreadyCached = carousel.areAllItemsLoaded(first, last);
				carousel.loadNextEvt.fire(first, last, alreadyCached);
			}
			
			if(showAnimation) {
				//carousel.debugMsg("scrollby: " + (-carousel.scrollAmountPerInc*inc));
	 			var nextParams = { points: { by: [-carousel.scrollAmountPerInc*inc, 0] } };
	 			if(carousel.isVertical()) {
	 				nextParams = { points: { by: [0, -carousel.scrollAmountPerInc*inc] } };
	 			}
 		
	 			carousel.scrollNextAnim = new YAHOO.util.Motion(carousel.carouselList, 
	 							nextParams, 
   								carousel.animSpeed, carousel.animationMethod);
				carousel.scrollNextAnim.animate();
			} else {
				if(carousel.isVertical()) {
					var currY = YAHOO.util.Dom.getY(carousel.carouselList);
										
					YAHOO.util.Dom.setY(carousel.carouselList, 
								currY - carousel.scrollAmountPerInc*inc);
				} else {
					var currX = YAHOO.util.Dom.getX(carousel.carouselList);
					YAHOO.util.Dom.setX(carousel.carouselList, 
								currX - carousel.scrollAmountPerInc*inc);
				}
			}
			
		}
		return false;
	},
	
	areAllItemsLoaded: function(first, last) {
		for(var i=first; i<=last; i++) {
			// if item is not loaded then at least one is not loaded
			if(!this.isValidObj(this.getCarouselItem(i))) {
				return false;
			}
		}
		return true;
	}, 
	
	_scrollPrev: function(e, carousel) {
		if(carousel.scrollPrevAnim.isAnimated()) {
			return false;
		}
		carousel._scrollPrevInc(carousel, carousel.scrollInc, (carousel.animSpeed != 0));
	},
	
	_scrollPrevInc: function(carousel, dec, showAnimation) {

		var newStart = carousel.start - dec;
		newStart = (newStart <= 1) ? 1 : (newStart);
		var newDec = carousel.start - newStart;
		carousel.start = newStart;
		
		// if prev is enabled && we are now at position 1, then disable
		if((carousel.prevEnabled == true) && (carousel.start == 1)) {
			carousel.disablePrev();
		}
		// if the next button is disabled and end is < size, then enable it
		if((carousel.nextEnabled == false) && 
						((carousel.start + carousel.numVisible - 1) < carousel.size)) {
			carousel.enableNext();
		}

		// if we are decrementing
		if(newDec > 0) {			
			if(carousel.isValidObj(carousel.prevHandler)) {
				var first = carousel.start;
				var last = carousel.start + carousel.numVisible - 1;
				var alreadyCached = carousel.areAllItemsLoaded(first, last);

				carousel.loadPrevEvt.fire(first, last, alreadyCached);
			}

			if(showAnimation) {
				//carousel.debugMsg("scrollby: " + (carousel.scrollAmountPerInc*newDec));
	 			var prevParams = { points: { by: [carousel.scrollAmountPerInc*newDec, 0] } };
	 			if(carousel.isVertical()) {
	 				prevParams = { points: { by: [0, carousel.scrollAmountPerInc*newDec] } };
	 			}
 		
	 			carousel.scrollPrevAnim = new YAHOO.util.Motion(carousel.carouselList,
	 							prevParams, 
   								carousel.animSpeed, carousel.animationMethod);
				carousel.scrollPrevAnim.animate();
			} else {
				if(carousel.isVertical()) {
					var currY = YAHOO.util.Dom.getY(carousel.carouselList);
					YAHOO.util.Dom.setY(carousel.carouselList, currY + 
							carousel.scrollAmountPerInc*newDec);				
				} else {
					var currX = YAHOO.util.Dom.getX(carousel.carouselList);
					YAHOO.util.Dom.setX(carousel.carouselList, currX + 
							carousel.scrollAmountPerInc*newDec);
				}
			}
		}
		
		return false;
	},
	
	isVertical: function() {
		return (this.orientation != "horizontal");
	},
	
	loadInitial: function() {
		this.start = 1;
		this.disablePrev();
		if(this.isValidObj(this.initHandler)) {
			this.loadInitialEvt.fire(this.start, this.start + this.numVisible -1);
		}
		
		if(this.autoPlay != 0) {
			this.autoPlayTimer = this.startAutoPlay();
		}		
    },
		
	disablePrev: function() {
		this.prevEnabled = false;
		if(this.isValidObj(this.prevButtonStateEvt)) {
			this.prevButtonStateEvt.fire(false, this.carouselPrev);
		}
		if(this.isValidObj(this.carouselPrev)) {
			YAHOO.util.Event.removeListener(this.carouselPrev, "click", this._scrollPrev);
		}
	},
	
	enablePrev: function() {
		this.prevEnabled = true;
		if(this.isValidObj(this.prevButtonStateEvt)) {
			this.prevButtonStateEvt.fire(true, this.carouselPrev);
		}
		if(this.isValidObj(this.carouselPrev)) {
			YAHOO.util.Event.addListener(this.carouselPrev, "click", this._scrollPrev, this);
		}
	},
		
	disableNext: function() {
		if(this.wrap) {
			return;
		}
		
		this.nextEnabled = false;
		if(this.isValidObj(this.nextButtonStateEvt)) {
			this.nextButtonStateEvt.fire(false, this.carouselNext);
		}
		if(this.isValidObj(this.carouselNext)) {
			YAHOO.util.Event.removeListener(this.carouselNext, "click", this._scrollNext);
		}
	},
	
	enableNext: function() {
		this.nextEnabled = true;
		if(this.isValidObj(this.nextButtonStateEvt)) {
			this.nextButtonStateEvt.fire(true, this.carouselNext);
		}
		if(this.isValidObj(this.carouselNext)) {
			YAHOO.util.Event.addListener(this.carouselNext, "click", this._scrollNext, this);
		}
	},
		
	getCarouselItem: function(idx) {
		var elemName = this.carouselElemID + "-item-" + idx;
 		var liElem = YAHOO.util.Dom.get(elemName);
		return liElem;	
	},
	
	isValidObj: function(obj) {

		if (null == obj) {
			return false;
		}
		if ("undefined" == typeof(obj) ) {
			return false;
		}
		return true;

	},


	/* should be moved */
	debugMsg: function(msg) 
	{
		var debugArea = document.getElementById("debug-area");
		debugArea.innerHTML = debugArea.innerHTML + "<br/>" + msg;
	},
	/* should be moved */
	clearDebug: function(msg) 
	{
		var debugArea = document.getElementById("debug-area");
		debugArea.innerHTML = "";
	}

}
