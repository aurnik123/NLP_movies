Description
	The folder contains five main folders. labeled_data contains our three training datasets. Scripts contains the scripts we scraped from IMSDB. 
Main contains the code we used to clean those scripts and load them into a sqlite database, and the code to train classifiers to assign emotion to these scripts. The outputs for selected scripts were output into the film_sentiment_predictions folder. 
Web contains the html and javascript code that aggregates and reads these emotion data points into a readable stacked bar chart format in a web app. The old code from the graph included in the poster presentation and is also included for posterity.

Installation
	Extract the files and run in place.

Execution
	Open the web/stacked.html file within your browser (we opened these files with IDEs such as Atom and PyCharm, on Chrome).
