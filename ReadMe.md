This project contains Three files: 
main.py - main file where we execute our functions'
data_quality_checking.py data quality detector
autoanalysis.py activated autoanalysis after we check data quality
 


outlier detection / sudden price changes (ip or down)

1. Calculate Percentage price changes
2. Calculate Volatility - calculate rolling standard deviation of the
percentage changes over a specified window size, excluding previous observation
3. Standardizing percentage changes (Rolling standard deviation serves as an estimate of recent volatility in perc price changes)
4. Apply threshold