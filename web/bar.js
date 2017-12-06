    var svg = d3.select("svg"),
        margin = {top: 20, right: 90, bottom: 50, left: 90},
        width = svg.attr("width") - margin.left - margin.right,
        height = svg.attr("height") - margin.top - margin.bottom
        g = svg.append("g").attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    svg.append("text")
    .attr("transform", "rotate(-90)")
    .attr("y", 0+margin.left/3)
    .attr("x",0 -(height / 2))
    .attr("dy", "1em")
    .style("text-anchor", "middle")
    .text("Percent of Scenes Displaying Emotion");

    svg.append("text")
    .attr("transform",
          "translate(" + (width/2 + margin.left) + " ," +
                         (height + margin.top + 35) + ")")
    .style("text-anchor", "middle")
    .text("Percent Through Movie By Scene");


    var z = d3.scaleOrdinal(["#e41a1c","#4daf4a","#984ea3","#ffff33","#377eb8","#ff7f00","white"]);

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


var x = d3.scaleBand()
    .rangeRound([0, width])
    .paddingInner(0.05)
    .align(0.1);

var y = d3.scaleLinear()
    .rangeRound([height, 0]);

    g.append("g")
        .attr("class", "xaxis")
        .attr("transform", "translate(0," + height + ")")
        .call(d3.axisBottom(x).tickFormat(function(d) {return d + "%"; }));

    g.append("g")
        .attr("class", "yaxis")
        .call(d3.axisLeft(y).ticks(10, "%"));




var keys = ["anger","disgust","fear","joy","sadness","surprise","neutral"];

var legend = g.append("g")
    .attr("font-family", "sans-serif")
    .attr("font-size", 10)
    .attr("text-anchor", "end")
  .selectAll("g")
  .data(keys.slice().reverse())
  .enter().append("g")
    .attr("transform", function(d, i) { return "translate(0," + i * 20 + ")"; });

legend.append("rect")
    .attr("x", width+ margin.left -19)
    .attr("width", 19)
    .attr("height", 19)
    .attr("fill", z)
     .style("stroke", "black");

legend.append("text")
    .attr("x", width + margin.left - 24)
    .attr("y", 9.5)
    .attr("dy", "0.32em")
    .text(function(d) { return d; });

var gran = 20;

function readCSV(filename,callback){
  d3.csv(filename, function(d, i, columns) {
    for (i = 1, t = 0; i < columns.length; ++i) t += d[columns[i]] = +d[columns[i]];
    //d.total = t;
    //remove
    d.scene = +d.scene
    return d;

  }, function(error, data) {
    if (error) throw error;

    //var keys = data.columns.slice(1);
    sceneMax = d3.max(data, function(d) { return d.scene; })
    for (var point in data){
        percentile = Math.ceil(gran*data[point].scene/sceneMax)*(100/gran);
        if(!o[percentile]){o[percentile] = {"p":percentile};};
        for (var prop in data[point]) {
            if (/anger|disgust|sadness|surprise|fear|joy|neutral/.test(prop) ) {
              if (o[percentile][prop]){
                o[percentile][prop] += data[point][prop];
              } else {o[percentile][prop] = data[point][prop]}
              //console.log(data[point][prop]);
            };
        }
    };
    callback(null);
  }
)

}


function makeGraph(path){
  q = d3.queue();

  percList ={};
  newData = [];
  o = {};

  path.forEach(function(d) {
    q.defer(readCSV, d);
  })

  q.awaitAll(function(error) {
    if (error) throw error;
    for (item in o){
      if(o[item].p){
        newData.push(o[item]);
      }
    }
    //console.log(o);

    for (bar in newData){
      t=0;
      for (val in newData[bar]) {
        t+=newData[bar][val];
      }
       t-= newData[bar].p;
      newData[bar].total = t;
      for (val in newData[bar]) {
        if(val != "p"){
          newData[bar][val] /= t ;
        }
      }

    }


    x.domain(newData.map(function(d) { return d.p; }));
    y.domain([0, d3.max(newData, function(d) { return d.total; })*0.45]).nice();
    z.domain(keys);

    g.append("g")
      .selectAll("g")
      .data(d3.stack().keys(keys)(newData))
      .enter().append("g")
        .attr("fill", function(d) { return z(d.key); })
      .selectAll("rect")
      .data(function(d) { return d; })
      .enter().append("rect")
        .attr("x", function(d) { return x(d.data.p); })
        .attr("y", function(d) { return y(d[1]); })
        .attr("height", function(d) { return y(d[0]) - y(d[1]); })
        .attr("width", x.bandwidth());


      svg.selectAll(".yaxis")
      .call(d3.axisLeft(y).ticks(10, "%"));

      svg.selectAll(".xaxis")
      .call(d3.axisBottom(x).tickFormat(function(d) {return ""+d-(100/gran)+"-"+d + "%"; }));

  });


};

d3.select('#opts')
  .on('change', function() {
    if(eval(d3.select(this).property('value')) == "grossing"){
      scripts = [ds1,ds2,ds3,ds4,ds5,ds6,ds7,ds8,ds9];
      makeGraph(scripts);
    }
    else if (eval(d3.select(this).property('value')) == "rated") {
      scripts = [ds11,ds12,ds13,ds14,ds15,ds16,ds17,ds18,ds19];
      makeGraph(scripts);
    }
    else {
      var newData = eval(d3.select(this).property('value'));
      makeGraph([newData]);
    }
});


makeGraph([ds1]);
