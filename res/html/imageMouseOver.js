function addMouseOverImage(element, imgSrc) {
    //debugOut('addMouseOverImage(): ' + imgSrc);
    var largeDiv = document.createElement('div');
    largeDiv.setAttribute('class', 'mouseOver');
    largeDiv.innerHTML = '<img src="' + imgSrc + '">';
    document.body.appendChild(largeDiv);

    element.largeDiv = largeDiv;

    element.addEventListener('mouseover', mouseMove, true);
    element.addEventListener('mousemove', mouseMove, true);
    element.addEventListener('mouseout', mouseOut, true);
}

var maxZoomFactor = 2.5;
function mouseMove(event) {
    var x = 0, y = 0, maxWidth = 0, maxHeight = 0, zoomFaktor = 0;
    // check which side of the cursor has more space left
    if(event.pageX < (window.innerWidth / 2)) {
      x = event.pageX + 10;
      maxWidth = window.innerWidth - (event.pageX + 50);
    } else {
      x = event.pageX - (5 + this.largeDiv.offsetWidth); // show large image left from cursor
      maxWidth = event.pageX - 20;
    }
    // zoom image to max size, so it still fits in the window
    maxHeight = window.innerHeight - 20;

    var imgObj = this.largeDiv.firstChild;
    zoomFaktor = Math.min(maxZoomFactor, maxHeight / imgObj.naturalHeight, maxWidth / imgObj.naturalWidth);
    imgObj.width = imgObj.naturalWidth * zoomFaktor;
    imgObj.height = imgObj.naturalHeight * zoomFaktor;

    // if the zoomed image still fits on the left side of the cursor, put it there
    if(event.pageX - (5 + this.largeDiv.offsetWidth) >= 0) {
      x = event.pageX - (5 + this.largeDiv.offsetWidth); // show large image left from cursor
    }
    y = event.pageY - (this.largeDiv.offsetHeight / 2); // show large image centered beside the cursor
    // don't let it slide out the top or bottom of the window
    y = Math.min(y, window.pageYOffset + window.innerHeight - this.largeDiv.offsetHeight - 5);
    y = Math.max(y, window.pageYOffset + 5);

    this.largeDiv.style.left = x + 'px';
    this.largeDiv.style.top = y + 'px';
    this.largeDiv.style.visibility = 'visible';
}

function mouseOut(event) {
    this.largeDiv.style.visibility = 'hidden';
}

imageExtentions = ['.gif', '.jpg', '.jpeg', '.png'];
function addForAllImageLinks(links) {
    //debugOut('addForAllImageLinks');
    for (var i = 0; i < links.length; i++) {
        var link = links[i];
        var linkedImageSrc = link.href;
        if (linkedImageSrc != undefined) {
            for (var j = 0; j < imageExtentions.length; j++) {
                if (linkedImageSrc.toLowerCase().indexOf(imageExtentions[j]) >= 0) {
                    addMouseOverImage(link, linkedImageSrc);
                    break;
                }
            }
        }
    }
}

function elementAdded(elementId) {
    //debugOut('elementAdded: ' + elementId);
    var element = document.getElementById(elementId);
    var links = element.getElementsByTagName('A');
    addForAllImageLinks(links);
}

function debugOut(text) {
    document.getElementById('debug').innerHTML += text + '\n';
}

function onLoad() {
    //debugOut('onLoad');
    addForAllImageLinks(document.getElementsByTagName('A'))
}
