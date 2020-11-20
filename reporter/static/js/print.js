var svg, width, height, projection, path, spinner;

var hideZips = ["60601", "60602", "60603", "60604", "60606", "60611", "60661"];

function createReportTables(json, feat) {
  var areaTableObj = {};
  json.features.forEach(function (d) {
    areaTableObj[d.properties[feat]] = d.properties.ci_count;
  });
  var featList = json.features
    .map(function (d) {
      return +d.properties[feat];
    })
    .sort(function (a, b) {
      return a - b;
    });

  if (feat === "ward") {
    var areaCol = "Ward";
    var brkInt = 25;
  } else {
    var areaCol = "Zip";
    var brkInt = 60630;
  }
  var mainDiv = document.querySelector("body");

  var areaTable1 = document.createElement("table");
  areaTable1.id = "area-table-1";
  var areaTable2 = document.createElement("table");
  areaTable2.id = "area-table-2";

  var topRow = document.createElement("tr");
  var areaHead = document.createElement("th");
  areaHead.appendChild(document.createTextNode(areaCol));
  var countHead = document.createElement("th");
  countHead.appendChild(document.createTextNode("Count"));
  topRow.appendChild(areaHead);
  topRow.appendChild(countHead);

  areaTable1.appendChild(topRow);
  areaTable2.appendChild(topRow.cloneNode(true));

  mainDiv.appendChild(areaTable1);
  mainDiv.appendChild(areaTable2);

  featList.forEach(function (i) {
    var tr = document.createElement("tr");
    if (parseInt(i) <= brkInt) {
      var tableEl = areaTable1;
    } else {
      var tableEl = areaTable2;
    }

    var areaEl = document.createElement("td");
    areaEl.appendChild(document.createTextNode(i.toString()));
    var countEl = document.createElement("td");
    countEl.appendChild(document.createTextNode(areaTableObj[i.toString()]));

    tr.appendChild(areaEl);
    tr.appendChild(countEl);
    tableEl.appendChild(tr);
  });
}

function handleGeoJson(json) {
  if (!svg.select("g.chicago").selectAll("path").size()) {
    var bounds = path.bounds(json);
    var s =
      0.95 /
      Math.max(
        (bounds[1][0] - bounds[0][0]) / width,
        (bounds[1][1] - bounds[0][1]) / height
      );
    var t = [
      (width - s * (bounds[1][0] + bounds[0][0])) / 2,
      (height - s * (bounds[1][1] + bounds[0][1])) / 2,
    ];
    projection.scale(s).translate(t);
  } else {
    svg.select("g.chicago").selectAll("text.area-label").remove();
    svg.select("g.chicago").selectAll("path").remove();
    svg.select("g.legend").remove();
  }

  var color = d3
    .scaleQuantize()
    .domain([
      0,
      d3.max(json.features, function (d) {
        if (d.properties.ci_count) {
          return d.properties.ci_count;
        }
        return 0;
      }),
    ])
    .range(colorbrewer[cbColors][5]);

  var legend = d3
    .select("svg")
    .append("g")
    .attr("class", "legend")
    .selectAll("g")
    .data(color.range())
    .enter()
    .append("g")
    .attr("class", "legend-item")
    .attr("transform", function (d, i) {
      var h = 25;
      var x = width * 0.8;
      var y = i * h + height * 0.2;
      return "translate(" + x + "," + y + ")";
    });

  legend
    .append("rect")
    .attr("width", 25)
    .attr("height", 25)
    .style("fill", function (d) {
      return d;
    });

  var legendText = "Calls/Issues by ";
  if (json.features[0].properties.zip) {
    legendText += "Zip";
    var areaProp = "zip";
  } else if (json.features[0].properties.ward) {
    legendText += "Ward";
    var areaProp = "ward";
  }

  svg
    .select("g.legend")
    .append("text")
    .attr("x", 0)
    .attr("y", -15)
    .attr("font-weight", "bold")
    .text(legendText)
    .attr("transform", "translate(" + width * 0.8 + "," + height * 0.2 + ")");

  legend
    .append("text")
    .attr("x", 35)
    .attr("y", 20)
    .text(function (d) {
      return color
        .invertExtent(d)
        .map(function (d) {
          return Math.floor(d);
        })
        .join("-");
    });

  svg
    .select("g.chicago")
    .selectAll("path")
    .data(json.features, function (d) {
      return d.properties[areaProp] + "-" + d.properties.ci_count;
    })
    .enter()
    .append("path")
    .attr("d", path)
    .attr("fill-opacity", 0.8)
    .attr("stroke", "#6F7070")
    .attr("stroke-opacity", 0.8)
    .attr("stroke-width", 1)
    .attr("fill", function (d) {
      return color(d.properties.ci_count);
    });

  svg
    .select("g.chicago")
    .selectAll("text.area-label")
    .data(json.features, function (d) {
      return d.properties[areaProp] + "-" + d.properties.ci_count;
    })
    .enter()
    .append("text")
    .attr("class", "area-label")
    .attr("transform", function (d) {
      return "translate(" + path.centroid(d) + ")";
    })
    .attr("dy", ".35em")
    .text(function (d) {
      if (hideZips.indexOf(d.properties[areaProp]) === -1) {
        return d.properties[areaProp];
      }
    });

  createReportTables(json, areaProp);
  if (areaProp === "zip") {
    var printNotice = document.getElementById("print-notice");
    var zipNotice = document.createElement("p");
    zipNotice.appendChild(
      document.createTextNode(
        "* Zip codes not labeled for space " + hideZips.join(", ")
      )
    );
    printNotice.appendChild(zipNotice);
  }
}

(function () {
  bbox = document.getElementsByTagName("svg")[0].getBoundingClientRect();
  width = bbox.width;
  height = bbox.height;
  svg = d3.select("svg");
  svg.append("g").attr("class", "chicago");

  projection = d3.geoMercator().scale(1).translate([0, 0]);
  path = d3.geoPath().projection(projection);

  handleGeoJson(geoDump);
})();
