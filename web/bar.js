    var svg = d3.select("svg"),
        margin = {top: 20, right: 20, bottom: 20, left: 40},
        width = svg.attr("width") - margin.left - margin.right,
        height = svg.attr("height") - margin.top - margin.bottom
        g = svg.append("g").attr("transform", "translate(" + margin.left + "," + margin.top + ")");


    var         z = d3.scaleOrdinal(["#e41a1c","#4daf4a","#984ea3","#ffff33","#377eb8","#ff7f00","white"]);

    var ds0 = [];
    var ds1 = "../film_sentiment_predictions/Avatar.csv";
    var ds2 = "../film_sentiment_predictions/Spider-Man.csv";
    var ds3 = "../film_sentiment_predictions/Pirates-of-the-Caribbean.csv";
    var ds4 = "../film_sentiment_predictions/Frozen.csv";
    var ds5 = "../film_sentiment_predictions/Star-Wars-Revenge-of-the-Si.csv";
    var ds6 = "../film_sentiment_predictions/Star-Wars-The-Force-Awakens.csv";
    var ds7 = "../film_sentiment_predictions/Lord-of-the-Rings-Return-of-the-King.csv";
    var ds8 = "../film_sentiment_predictions/Mission-Impossible.csv";
    var ds9 = "../film_sentiment_predictions/Shrek-the-Third.csv";
    var ds10 = [];
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
        .call(d3.axisBottom(x));

    g.append("g")
        .attr("class", "yaxis")
        .call(d3.axisLeft(y).ticks(null, "s"));


function makeGraph(path){
    percList ={};
    d3.csv(path, function(d, i, columns) {
      for (i = 1, t = 0; i < columns.length; ++i) t += d[columns[i]] = +d[columns[i]];
      //d.total = t;
      //remove
      d.scene = +d.scene
      return d;

    }, function(error, data) {
      if (error) throw error;

      var keys = data.columns.slice(1);
      sceneMax = d3.max(data, function(d) { return d.scene; })
      o = {};
      for (var point in data){
          percentile = Math.ceil(10*data[point].scene/sceneMax)*10;
          if(!o[percentile]){o[percentile] = {"p":percentile};};
          for (var prop in data[point]) {
              if (/anger|disgust|sadness|surprise|fear|joy|neutral/.test(prop) ) {
                if (o[percentile][prop]){
                  o[percentile][prop] += data[point][prop];
                } else {o[percentile][prop] = data[point][prop]}
                //console.log(o);
              };
          }
      };
      newData = [];
      for (item in o){
        if(o[item].p){
          newData.push(o[item]);
        }
      }
      for (bar in newData){
        t=0;
        for (val in newData[bar]) {
          t+=newData[bar][val];
        }
         t-= newData[bar].p;
        newData[bar].total = t;
      }
      //console.log(newData);


      x.domain(newData.map(function(d) { return d.p; }));
      y.domain([0, d3.max(newData, function(d) { return d.total; })]).nice();
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


      var legend = g.append("g")
          .attr("font-family", "sans-serif")
          .attr("font-size", 10)
          .attr("text-anchor", "end")
        .selectAll("g")
        .data(keys.slice().reverse())
        .enter().append("g")
          .attr("transform", function(d, i) { return "translate(0," + i * 20 + ")"; });

      legend.append("rect")
          .attr("x", width - 19)
          .attr("width", 19)
          .attr("height", 19)
          .attr("fill", z);

      legend.append("text")
          .attr("x", width - 24)
          .attr("y", 9.5)
          .attr("dy", "0.32em")
          .text(function(d) { return d; });



        svg.selectAll(".yaxis")
        .call(d3.axisLeft(y).ticks(null, "s"));

        svg.selectAll(".xaxis")
        .call(d3.axisBottom(x));
    });
};

d3.select('#opts')
  .on('change', function() {
    var newData = eval(d3.select(this).property('value'));
    makeGraph(newData);
});


makeGraph(ds1);
