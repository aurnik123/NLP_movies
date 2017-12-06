var svg = d3.select("svg"),
    margin = {top: 20, right: 20, bottom: 20, left: 40},
    width = svg.attr("width") - margin.left - margin.right,
    height = svg.attr("height") - margin.top - margin.bottom;

var x = d3.scaleLinear().range([0, width]),
    y = d3.scaleLinear().range([height, 0]),
    z = d3.scaleOrdinal(["#e41a1c","#4daf4a","#984ea3","#ffff33","#377eb8","#ff7f00","white"]);

var ds0 = "grossing";
var ds1 = "../film_sentiment_predictions/Avatar.csv";
var ds2 = "../film_sentiment_predictions/Spider-Man.csv";
var ds3 = "../film_sentiment_predictions/Pirates-of-the-Caribbean.csv";
var ds4 = "../film_sentiment_predictions/Frozen.csv";
var ds5 = "../film_sentiment_predictions/Star-Wars-Revenge-of-the-Si.csv";
var ds6 = "../film_sentiment_predictions/Star-Wars-The-Force-Awakens.csv";
var ds7 = "../film_sentiment_predictions/Lord-of-the-Rings-Return-of-the-King.csv";
var ds8 = "../film_sentiment_predictions/Mission-Impossible.csv";
var ds9 = "../film_sentiment_predictions/Shrek-the-Third.csv";
var ds10 = "rated";
var ds11 = "../film_sentiment_predictions/Boyhood.csv";
var ds12 = "../film_sentiment_predictions/Lost-in-Translation.csv";
var ds13 = "../film_sentiment_predictions/12-Years-a-Slave.csv";
var ds14 = "../film_sentiment_predictions/Social-Network,-The.csv";
var ds15 = "../film_sentiment_predictions/Zero-Dark-Thirty.csv";
var ds16 = "../film_sentiment_predictions/Wall-E.csv";
var ds17 = "../film_sentiment_predictions/Sideways.csv";
var ds18 = "../film_sentiment_predictions/Amour.csv";
var ds19 = "../film_sentiment_predictions/Crouching-Tiger,-Hidden-Dragon.csv";
var ds20 = "../film_sentiment_predictions/Hudson-Hawk.csv";
var ds21 = "../film_sentiment_predictions/Catwoman.csv";


//NEEDS A CSV WITH SCENES IN ORDER, scene as first column
function makeGraph(path){
  var stack = d3.stack();
  var sceneMax = 1;
  var area = d3.area()
      .x(function(d, i) { return x((d.data.scene-1)/sceneMax); })
      .y0(function(d) { return y(d[0]); })
      .y1(function(d) { return y(d[1]); });

  var g = svg.append("g")
      .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

  var div = d3.select("body").append("div")
      .attr("class", "tooltip")

    d3.csv(path, norm, function(error, data) {
      if (error) throw error;
      var keys = data.columns.slice(1);
      sceneMax = d3.extent(data, function(d) { return d.scene; })[1]- 1;
      x.domain([0,1]);
      z.domain(keys);
      stack.keys(keys);


      var layer = g.selectAll(".layer")
        .data(stack(data))
        .enter().append("g")
        .attr("class", "layer")
        .on("mouseover", function(d,i) {
          console.log([d[i].data["anger"],d[i].data["disgust"],]);
					div.transition()
							.duration(0)
							.style("opacity", 1)
					div.html([d[i].data["anger"],d[i].data["disgust"],])
          .style("left", (d3.event.pageX) + "px")
          .style("top", (d3.event.pageY) + "px")
				})
				.on("mouseout", function(d) {
						div.transition()
								.duration(0)
								.style("opacity", 0)
				});

      layer.append("path")
          .attr("class", "area")
          .style("fill", function(d) { return z(d.key); })
          .attr("d", area);

      g.append("g")
          .attr("class", "axis axis--x")
          .attr("transform", "translate(0," + height + ")")
          .call(d3.axisBottom(x).ticks(10, "%"));

      g.append("g")
          .attr("class", "axis axis--y")
          .call(d3.axisLeft(y).ticks(10, "%"));


    });
}

function norm(d, i, columns) {
  sum = 0
  for (thing in d){
    if(thing!="scene"){
      sum += +d[thing];
    }
  }
  if (sum !== 0) {
      for (thing in d) {
        if(thing!="scene") {
            d[thing] = +d[thing]/sum;
        }
      }
  }
  d["scene"] = +d["scene"];
  return d;
}
//call makeGraph(csvfilepath) externally with whateever your formatted data values are
makeGraph("../film_sentiment_predictions/Avatar.csv");

// handle on click event
d3.select('#opts')
  .on('change', function() {
    var newData = eval(d3.select(this).property('value'));
    makeGraph(newData);
});
