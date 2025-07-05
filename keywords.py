import nltk
from collections import Counter
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Download required NLTK data
nltk.download('punkt')
nltk.download('stopwords')

def extract_keywords(text, top_n=10):
    words = word_tokenize(text.lower())
    stop_words = set(stopwords.words('english'))
    words = [w for w in words if w.isalpha() and w not in stop_words]
    freq = Counter(words).most_common(top_n)
    hashtags = [f"#{word}" for word, _ in freq]
    return hashtags

