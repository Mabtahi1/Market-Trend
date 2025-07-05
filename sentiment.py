from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

def analyze_sentiment(text):
    score = analyzer.polarity_scores(text)
    sentiment = "Positive" if score['compound'] > 0.05 else "Negative" if score['compound'] < -0.05 else "Neutral"
    return sentiment, score

