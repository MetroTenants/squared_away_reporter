var svg, width, height, projection, path, spinner, tooltip, cbColors;

function handleGeoJson(geoPath) {
  d3.json(geoPath, function(json) {
    if (!svg.select("g.chicago").selectAll("path").size()) {
      var bounds = path.bounds(json);
      var s = 0.95 / Math.max((bounds[1][0] - bounds[0][0]) / width, (bounds[1][1] - bounds[0][1]) / height);
      var t = [(width - s * (bounds[1][0] + bounds[0][0])) / 2, (height - s * (bounds[1][1] + bounds[0][1])) / 2];
      projection.scale(s).translate(t);
      tooltip = d3.select("body")
        .append("div")
        .style("visibility", "hidden")
        .style("font-size", "16px")
        .style("padding", "10px")
        .style("z-index", "10")
        .style("position", "absolute")
        .style("background-color", "lightgrey");
    }
    else {
      svg.select("g.chicago")
        .selectAll("path").remove();
      svg.select("g.legend").remove();
    }

    var color = d3.scaleQuantize()
        .domain([0, d3.max(json.features, function(d) {
          if (d.properties.ci_count) {
            return d.properties.ci_count;
          }
          return 0;
        })])
        .range(colorbrewer[cbColors][5]);

    var legend = d3.select('svg')
        .append("g")
          .attr("class", "legend")
        .selectAll("g")
        .data(color.range())
        .enter()
        .append('g')
          .attr('class', 'legend-item')
          .attr('transform', function(d, i) {
            var h = 25;
            var x = 0;
            var y = (i * h) + (height * 0.7);
            return 'translate(' + x + ',' + y + ')';
        });

    legend.append('rect')
        .attr('width', 25)
        .attr('height', 25)
        .style('fill', function(d) { return d; });

    var legendText = "Calls/Issues by ";
    if (json.features[0].properties.zip) {
      var tooltA = "Zip";
      legendText += tooltA;
      var areaProp = "zip";
    }
    else if (json.features[0].properties.ward) {
      var tooltA = "Ward";
      legendText += tooltA;
      var areaProp = "ward";
    }

    svg.select('g.legend').append("text")
      .attr('x', 0)
      .attr('y', -15)
      .attr('font-weight', 'bold')
      .text(legendText)
      .attr('transform', 'translate(0,' + (height*0.7) + ')');

    legend.append('text')
        .attr('x', 35)
        .attr('y', 20)
        .text(function(d) {
          return color.invertExtent(d).map(function(d) { return Math.floor(d); }).join("-");
        });

    svg.select("g.chicago")
      .selectAll("path")
        .data(json.features, function(d) {
          return d.properties[areaProp] + "-" + d.properties.ci_count;
        })
        .enter().append("path")
          .attr("d", path)
          .attr("fill-opacity", 0.8)
          .attr("stroke", "#6F7070")
          .attr("stroke-opacity", 0.8)
          .attr("stroke-width", 1)
          .attr("fill", function(d) { return color(d.properties.ci_count);})
          .on("mouseover", function(d){
            return tooltip.style("visibility", "visible")
              .html("<b>" + tooltA + "</b>: " + d.properties[areaProp] + "<br><b>Count</b>: " + d.properties.ci_count)
          })
	        .on("mousemove", function(){return tooltip.style("top", (event.pageY-10)+"px").style("left",(event.pageX+10)+"px");})
	        .on("mouseout", function(){return tooltip.style("visibility", "hidden");});;

    spinner.style.display = "none";
  });
}

//pads left
String.prototype.lpad = function(padString, length) {
	var str = this;
    while (str.length < length)
        str = padString + str;
    return str;
};

(function() {
  bbox = document.getElementsByTagName("svg")[0].getBoundingClientRect();
  width = bbox.width;
  height = bbox.height;
  svg = d3.select("svg");
  spinner = document.querySelector("div.loader");

  // Setting the start and end date inputs
  var startDate = document.getElementById("start_date");
  var endDate = document.getElementById("end_date");

  var dt = new Date();
  var mn = (dt.getMonth() + 1).toString().lpad("0", 2);
  var dy = dt.getDate().toString().lpad("0", 2);
  startDate.value = (dt.getFullYear() - 1) + "-" + mn + "-" + dy;
  endDate.value = dt.getFullYear() + "-" + mn + "-" + dy;

  svg.append("g")
    .attr("class", "chicago");

  projection = d3.geoMercator().scale(1).translate([0,0]);
  path = d3.geoPath().projection(projection);

  var button = document.querySelector("button");
  button.addEventListener("click", function() {
    spinner.style.display = "inherit";

    var queryUrl = "filter-geo?";
    var geog = document.getElementById("geog");
    cbColors = document.querySelector("#color_choice").value;
    var startDate = document.getElementById("start_date");
    var endDate = document.getElementById("end_date");
    var categoryValues = document.querySelectorAll("#categories option:checked");
    var zipCodes = document.querySelectorAll("#zip_codes option:checked");

    var queryArgs = [];

    queryArgs.push("geog=" + geog.value);
    queryArgs.push("color_choice=" + cbColors);

    if (startDate.value) {
      queryArgs.push("start_date=" + startDate.value);
    }
    if (endDate.value) {
      queryArgs.push("end_date=" + endDate.value);
    }
    if (categoryValues) {
      var catArr = Array.prototype.slice.call(categoryValues);
      queryArgs.push("categories=" + catArr.map(function(c){return c.value;}).join(","));
    }
    if (zipCodes) {
      var zipArr = Array.prototype.slice.call(zipCodes);
      queryArgs.push("zip_codes=" + zipArr.map(function(z){return z.value;}).join(","));
    }
    queryUrl += queryArgs.join("&");

    var csvLink = document.getElementById("csvLink");
    csvLink.href = "filter-csv?" + queryArgs.join("&");
    var printLink = document.getElementById("printLink");
    printLink.href = "print?" + queryArgs.join("&");

    handleGeoJson(queryUrl);
  });
})()
