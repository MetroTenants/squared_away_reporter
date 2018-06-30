function barChart() {
  var margin = { top: 10, right: 10, bottom: 60, left: 150 },
    width = 350,
    height = 350,
    labelValue = function (d) { return d.label; },
    dataValue = function (d) { return +d.value; },
    bandPadding = 0.1,
    color = "#b2ebf2";

  function chart(selection) {
    selection.each(function (data) {
      data = data.map(function (d, i) {
        return { label: labelValue(d), value: dataValue(d) };
      }).sort(function (a, b) { return d3.descending(a.value, b.value); });
      var x = d3.scaleBand().rangeRound([0, height - margin.top - margin.bottom]).padding(bandPadding),
        y = d3.scaleLinear().rangeRound([0, width - margin.left - margin.right]);

      x.domain(data.map(function (d) { return d.label; }));
      y.domain([0, d3.max(data, dataValue)]);

      var svg = d3.select(this).selectAll("svg").data([data]);
      var gEnter = svg.enter().append("svg").append("g");
      gEnter.append("g").attr("class", "axis x");
      gEnter.append("g").attr("class", "axis y").append("text");

      var svg = selection.select("svg");
      svg.attr('width', width).attr('height', height);
      var g = svg.select("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

      g.select("g.axis.x")
        .call(d3.axisLeft(x));

      g.selectAll("g.axis text")
        .style("font-size", "11px");

      g.select("g.axis.y")
        .attr("class", "axis y")
        .attr("transform", "translate(0," + (height - margin.bottom - margin.top) + ")")
        .call(d3.axisBottom(y).ticks(5));

      g.select("g.axis.y text")
        .attr("transform", "rotate(-90)")
        .attr("y", 6)
        .attr("dy", "0.71em")
        .attr("text-anchor", "end");


      var rects = g.selectAll("rect.bar")
        .data(data, function (d) { return d.label; });

      rects.exit().remove();
      rects.enter().append("rect")
        .merge(rects)
        .attr("class", "bar")
        .attr("x", "1")
        .attr("y", function (d) { return x(d.label); })
        .attr("fill", color)
        .attr("height", x.bandwidth())
        .transition()
        .duration(750)
        .attr("width", function (d) { return y(dataValue(d)); });
    });
  }

  chart.margin = function (_) {
    if (!arguments.length) return margin;
    margin = _;
    return chart;
  };

  chart.width = function (_) {
    if (!arguments.length) return width;
    width = _;
    return chart;
  };

  chart.height = function (_) {
    if (!arguments.length) return height;
    height = _;
    return chart;
  };

  chart.labelValue = function (_) {
    if (!arguments.length) return labelValue;
    labelValue = _;
    return chart;
  };

  chart.dataValue = function (_) {
    if (!arguments.length) return dataValue;
    dataValue = _;
    return chart;
  };

  chart.color = function (_) {
    if (!arguments.length) return color;
    color = _;
    return chart;
  };

  return chart;
}

//pads left
String.prototype.lpad = function (padString, length) {
  var str = this;
  while (str.length < length)
    str = padString + str;
  return str;
};

(function () {
  var spinner = document.querySelector("div.loader");
  var svg = d3.select("svg");
  var bars = barChart();

  function resize() {
    if (svg.empty()) {
      return;
    }
    bars.width(+svg.style("width").replace(/(px)/g, ""))
      .height(+svg.style("height").replace(/(px)/g, ""));
    svg.call(bars);
  }

  d3.select(window).on('resize', resize);

  function handleData(data) {
    var wards = document.querySelectorAll("#wards option:checked");
    if (!wards.length) {
      wards = document.querySelectorAll("#wards option");
    }
    var wardList = Array.prototype.slice.call(wards).map(function (w) { return w.value; });
    var wardData = wardList.map(function (w) {
      return data[w];
    }).reduce(function (a, b) {
      Object.keys(b).forEach(function (k) {
        if (b.hasOwnProperty(k)) {
          a[k] = (a[k] || 0) + b[k];
        }
      });
      return a;
    }, {});

    categoryData = Object.keys(wardData).map(function (key) {
      return { label: key, value: wardData[key] };
    });
    svg.datum(categoryData).call(bars);
    spinner.style.display = "none";
    resize();
  }

  // Setting the start and end date inputs
  var startDate = document.getElementById("start_date");
  var endDate = document.getElementById("end_date");

  var dt = new Date();
  var mn = (dt.getMonth() + 1).toString().lpad("0", 2);
  var dy = dt.getDate().toString().lpad("0", 2);
  startDate.value = (dt.getFullYear() - 1) + "-" + mn + "-" + dy;
  endDate.value = dt.getFullYear() + "-" + mn + "-" + dy;

  var button = document.querySelector("#updatevals");
  button.addEventListener("click", function () {
    spinner.style.display = "inherit";

    var queryUrl = "breakdown-wards?";
    cbColors = document.querySelector("#color_choice").value;

    bars.color(colorbrewer[cbColors][5][3]);
    d3.select("#chart").call(bars);

    var startDate = document.getElementById("start_date");
    var endDate = document.getElementById("end_date");
    var categoryValues = document.querySelectorAll("#categories option:checked");
    var wards = document.querySelectorAll("#wards option:checked");
    var reportTitle = document.getElementById("report_title").value;
    var reportSubTitle = document.getElementById("wardTimeLabel");
    var wardStr;

    var queryArgs = [];

    queryArgs.push("color_choice=" + cbColors);

    if (startDate.value) {
      queryArgs.push("start_date=" + startDate.value);
    }
    if (endDate.value) {
      queryArgs.push("end_date=" + endDate.value);
    }
    if (categoryValues) {
      var catArr = Array.prototype.slice.call(categoryValues);
      queryArgs.push("categories=" + catArr.map(function (c) { return c.value; }).join(","));
    }
    if (wards) {
      var wardArr = Array.prototype.slice.call(wards).map(function (w) { return w.value; });
      queryArgs.push("wards=" + wardArr.join(","));
      if (wardArr.length === 1) {
        wardStr = "Ward " + wardArr[0]
      } else {
        wardStr = "Wards " + wardArr.join(", ");
      }
    } else {
      wardStr = "All Wards";
    }
    reportSubTitle.innerHTML = wardStr + ": " + startDate.value + " - " + endDate.value;
    if (reportTitle) {
      document.getElementById("reportTitle").innerHTML = reportTitle;
    }
    queryUrl += queryArgs.join("&");

    d3.json(queryUrl, handleData);
  });
})()
