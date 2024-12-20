import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import PyPDF2  # For PDF file reading
import pandas as pd
from newspaper import Article  # For website content extraction
import nltk
nltk.download('punkt')
import google.generativeai as genai
import os
from io import BytesIO
# nltk.download('punkt')
# nltk.download('wordnet')
# nltk.download('omw-1.4')
# nltk.download('punkt_tab')

# Ensure punkt data is downloaded


# Download the punkt tokenizer models
nltk.download('punkt')

# Streamlit webpage title
st.title('Comprehensive Oil Price Trend Analyzer')

# Function to extract links related to specific keywords with pagination
def find_links_for_keywords_with_pagination(url, keywords, max_pages=3):
    try:
        matching_links = []  # List to store all matching links across pages
        current_page = 1  # Start from the first page
        while current_page <= max_pages and url:
            response = requests.get(url, verify=False)
            response.raise_for_status()
            page_content = response.content
            soup = BeautifulSoup(page_content, 'html.parser')
            links = soup.find_all('a', href=True)
            keyword_pattern = re.compile('|'.join(keywords), re.IGNORECASE)

            for link in links:
                href = link['href']
                text = link.get_text()
                if keyword_pattern.search(href) or keyword_pattern.search(text):
                    matching_links.append(href)

            next_page_link = soup.find('a', text=re.compile(r'Next|›', re.IGNORECASE))
            if next_page_link:
                next_page_url = next_page_link['href']
                if not next_page_url.startswith('http'):
                    next_page_url = requests.compat.urljoin(url, next_page_url)
                url = next_page_url
                current_page += 1
            else:
                break
        return matching_links
    except requests.exceptions.RequestException as e:
        st.error(f"An error occurred while fetching the URL: {e}")
        return []

# Function to extract PDF download links with pagination
def find_pdf_links_with_pagination(url, max_pages=3):
    try:
        pdf_links = []  # List to store all PDF links across pages
        current_page = 1  # Start from the first page
        while current_page <= max_pages and url:
            response = requests.get(url, verify=False)
            response.raise_for_status()
            page_content = response.content
            soup = BeautifulSoup(page_content, 'html.parser')
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                if href.endswith('.pdf'):
                    pdf_links.append(href)
            next_page_link = soup.find('a', text=re.compile(r'Next|›', re.IGNORECASE))
            if next_page_link:
                next_page_url = next_page_link['href']
                if not next_page_url.startswith('http'):
                    next_page_url = requests.compat.urljoin(url, next_page_url)
                url = next_page_url
                current_page += 1
            else:
                break
        return pdf_links
    except requests.exceptions.RequestException as e:
        st.error(f"An error occurred while fetching the URL: {e}")
        return []

# Function to extract text from the first two pages of a PDF
# def extract_text_from_pdf(pdf_file):
#     try:
#         pdf_reader = PyPDF2.PdfReader(pdf_file)
#         text = ''
#         for page_num in range(min(2, len(pdf_reader.pages))):
#             page = pdf_reader.pages[page_num]
#             text += page.extract_text()
#         return text
#     except Exception as e:
#         st.error(f"An error occurred while processing the PDF file: {e}")
#         return None

def extract_text_from_pdf(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ''.join(page.extract_text() for page in pdf_reader.pages[:2])
        return text
    except Exception as e:
        st.error(f"An error occurred while processing the PDF file: {e}")
        return None


# Function to fetch and download PDF from URL and extract text
def download_and_extract_pdf_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        pdf_file = BytesIO(response.content)
        extracted_text = extract_text_from_pdf(pdf_file)
        return extracted_text
    except Exception as e:
        st.error(f"An error occurred while downloading or extracting the PDF from {url}: {e}")
        return None

# Function to fetch and parse website content
def extract_text_from_website(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        st.error(f"An error occurred while fetching content from {url}: {e}")
        return None

# # Function to filter and extract price information and trends
# def extract_price_trends(text):
#     PRICE_KEYWORDS = ['price', 'increase', 'decrease', 'rate', 'cost', 'change', 'up', 'down']
#     PRODUCTS = ['Palm Oil', 'Rapeseed Oil', 'PFAD', 'Sunflower Oil']
#     price_regex = r'(\d+[\.\,]?\d*)'
#     sentences = nltk.sent_tokenize(text)
#     relevant_sentences = []
#     price_trends = {product: '' for product in PRODUCTS}
#     for sentence in sentences:
#         for product in PRODUCTS:
#             if product.lower() in sentence.lower():
#                 if any(keyword in sentence.lower() for keyword in PRICE_KEYWORDS):
#                     price_match = re.search(price_regex, sentence)
#                     trend = None
#                     if "increase" in sentence.lower() or "up" in sentence.lower():
#                         trend = "up"
#                     elif "decrease" in sentence.lower() or "down" in sentence.lower():
#                         trend = "down"
#                     if trend and price_match:
#                         price_trends[product] = f'{product} price is going {trend}: {price_match.group(0)}'
#                         relevant_sentences.append(f'{product}: {sentence}')
#     return price_trends, ' '.join(relevant_sentences)


import re
import nltk
from datetime import datetime

def extract_price_trends(text):
    # Define relevant keywords and regex patterns for broader data extraction
    PRICE_KEYWORDS = ['price', 'increase', 'decrease', 'rate', 'cost', 'change', 'up', 'down', 'rise', 'drop', 'fall']
    SUPPLY_KEYWORDS = ['supply', 'demand', 'shortage', 'surplus', 'production', 'export', 'import', 'availability']
    FACTORS_KEYWORDS = ['geopolitical', 'war', 'conflict', 'sanctions', 'climate', 'weather', 'tariffs', 'embargo']
    PRODUCTS = ['Palm Oil', 'Rapeseed Oil', 'PFAD', 'Sunflower Oil']

    price_trends = {product: [] for product in PRODUCTS}  # Store multiple sentences for each product

    # Regex pattern for numbers and dates
    price_regex = r'(\d+[\.,]?\d*)'
    date_regex = r'(\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b)'

    # Tokenize the text into sentences
    sentences = nltk.sent_tokenize(text)
    
    # Loop through sentences and extract relevant information
    for sentence in sentences:
        for product in PRODUCTS:
            if product.lower() in sentence.lower():
                # Check if sentence has keywords related to price, supply, or factors
                if any(keyword in sentence.lower() for keyword in PRICE_KEYWORDS + SUPPLY_KEYWORDS + FACTORS_KEYWORDS):
                    # Identify price movement (up, down) if mentioned
                    trend = None
                    if "increase" in sentence.lower() or "up" in sentence.lower() or "rise" in sentence.lower():
                        trend = "up"
                    elif "decrease" in sentence.lower() or "down" in sentence.lower() or "fall" in sentence.lower() or "drop" in sentence.lower():
                        trend = "down"
                    
                    # Extract price, trend, and date information if available
                    price_match = re.search(price_regex, sentence)
                    date_match = re.search(date_regex, sentence)
                    
                    # Format date if found
                    if date_match:
                        date_str = date_match.group(1)
                    else:
                        date_str = "No specific date"

                    if trend and price_match:
                        trend_info = f'{product} price is going {trend}: {price_match.group(0)} on {date_str}'
                    else:
                        trend_info = f'{product} - No clear price trend, but relevant: {sentence} (Date: {date_str})'

                    # Add the sentence and trend info to the product’s list of trends
                    price_trends[product].append(trend_info)

    # Format results for easier display
    formatted_trends = {}
    for product, trends in price_trends.items():
        formatted_trends[product] = "\n".join(trends) if trends else "No significant data found for this product."

    # Combine all sentences into one string for additional analysis or summarization
    all_relevant_sentences = ' '.join([' '.join(trends) for trends in price_trends.values()])

    return formatted_trends, all_relevant_sentences



# Function to generate content using the language model
os.environ['GOOGLE_API_KEY'] = "AIzaSyB_0W_3KBVKNI0Tygo2iBVMhfbiCwS9VfY"
genai.configure(api_key=os.environ['GOOGLE_API_KEY'])
model = genai.GenerativeModel('gemini-pro')

def llm_function(query):
    response = model.generate_content(query)
    return response.text

# Input field for the URL
url = st.text_input('Enter the URL to search for links:', '')

# Input field for max number of pages to search
max_pages = st.number_input('Enter the number of pages to search (pagination):', min_value=1, value=3)

# Define keywords for the search
keywords = ["Palm Oil", "PFAD", "Sunflower Oil", "Bio-diesel"]

# Button to trigger the link search for keywords
if st.button('Find Keyword Links'):
    if url:
        with st.spinner('Fetching and analyzing links...'):
            matching_links = find_links_for_keywords_with_pagination(url, keywords, max_pages)
        if matching_links:
            st.success(f'Found {len(matching_links)} matching links for keywords across {max_pages} pages:')
            for link in matching_links:
                st.write(link)
        else:
            st.warning('No matching links found for the given keywords.')
    else:
        st.error('Please enter a valid URL.')

# Button to trigger the search for PDF download links
if st.button('Find PDF Links'):
    if url:
        with st.spinner('Fetching and analyzing PDF links...'):
            pdf_links = find_pdf_links_with_pagination(url, max_pages)
        if pdf_links:
            st.success(f'Found {len(pdf_links)} PDF links across {max_pages} pages:')
            st.spinner("Pdf links fetched.... Extracting data")
            combined_text = ''
            all_pdf_text = ''
            for pdf_url in pdf_links:
                pdf_text = download_and_extract_pdf_from_url(pdf_url.strip())
                if pdf_text:
                    all_pdf_text += pdf_text + ' '
            combined_text += all_pdf_text
            price_trends, relevant_info = extract_price_trends(combined_text)
            selected_question = """
            Summarize the document, focusing on the price fluctuations of palm oil and soybean oil, with particular emphasis on the significant changes that have occurred in the last two months.Presnt if the prices have increased or decreased. Present the key factors driving these recent price movements in bullet points, including global demand, supply, and geopolitical events. Return the data in Bullet form"""
            print ('\n\n\n\n')
            print (combined_text)
            print('-----------------------------------------')
            query = f'{selected_question} {combined_text}'
            response_text = llm_function(query)
            if response_text:
                st.write(response_text)
            else:
                st.write("No content generated.")
            for pdf_link in pdf_links:
                st.write(pdf_link)
        else:
            st.warning('No PDF links found on the page.')
    else:
        st.error('Please enter a valid URL.')
