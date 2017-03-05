var svg, width, height, projection, path, spinner;

function handleGeoJson(json) {
  if (!svg.select("g.chicago").selectAll("path").size()) {
    var bounds = path.bounds(json);
    var s = 0.95 / Math.max((bounds[1][0] - bounds[0][0]) / width, (bounds[1][1] - bounds[0][1]) / height);
    var t = [(width - s * (bounds[1][0] + bounds[0][0])) / 2, (height - s * (bounds[1][1] + bounds[0][1])) / 2];
    projection.scale(s).translate(t);
  }
  else {
    svg.select("g.chicago")
      .selectAll("path").remove();
    svg.select("g.legend").remove();
  }

  var color = d3.scaleQuantize()
      .domain([0, d3.max(json.features, function(d) {
        if (d.properties.call_issue_count) {
          return d.properties.call_issue_count;
        }
        return 0;
      })])
      .range(colorbrewer.Blues[5]);

  // NEED TO HAVE A TABLE OF ZIPS/WARDS ON SIDE

  var legend = d3.select('svg')
      .append("g")
        .attr("class", "legend")
      .selectAll("g")
      .data(color.range())
      .enter()
      .append('g')
        .attr('class', 'legend-item')
        // CHANGE THIS TO BE RIGHT SIDE
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
    legendText += "Zip Code";
  }
  else if (json.features[0].properties.ward) {
    legendText += "Ward";
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
        return d.properties.ward + "-" + d.properties.call_issue_count;
      })
      .enter().append("path")
        .attr("d", path)
        .attr("fill-opacity", 0.8)
        .attr("stroke", "#6F7070")
        .attr("stroke-opacity", 0.8)
        .attr("stroke-width", 1)
        .attr("fill", function(d) { return color(d.properties.call_issue_count);});
}

(function() {
  bbox = document.getElementsByTagName("svg")[0].getBoundingClientRect();
  width = bbox.width;
  height = bbox.height;
  svg = d3.select("svg");
  svg.append("g")
    .attr("class", "chicago");

  projection = d3.geoMercator().scale(1).translate([0,0]);
  path = d3.geoPath().projection(projection);

  handleGeoJson(geoDump);
})()
