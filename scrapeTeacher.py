from requests_html import HTMLSession
import os
from bs4 import BeautifulSoup
from fpdf import FPDF

# Base URL
BASE_URL = "http://isb.nu.edu.pk"

# Directory to save PDFs
os.makedirs("Faculty_PDFs", exist_ok=True)

def save_to_pdf(file_name, content):
    """Save the content to a PDF file."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in content.split("\n"):
        pdf.multi_cell(0, 10, line)
    pdf.output(file_name)

def extract_faculty_links():
    """Extract faculty detail page links using requests-html."""
    session = HTMLSession()
    response = session.get(f"{BASE_URL}/Faculty/allfaculty")
    response.html.render(timeout=20)  # Render JavaScript content

    soup = BeautifulSoup(response.html.html, "html.parser")
    faculty_links = []

    for card in soup.select("div.our-team ul.social a"):
        link = card.get("href")
        if link and "/Faculty/Details/" in link:
            faculty_links.append(BASE_URL + link)
    return faculty_links

def parse_faculty_details(url):
    """Parse faculty details from the detail page."""
    session = HTMLSession()
    response = session.get(url)
    response.html.render(timeout=20)  # Render JavaScript content

    soup = BeautifulSoup(response.html.html, "html.parser")

    # Extract faculty name
    name_tag = soup.select_one("div.team-content h3.title")
    name = name_tag.text.strip() if name_tag else "Unknown Name"

    # Extract JavaScript-embedded data (Introduction, Experience, Publication)
    script = soup.find("script", text=lambda t: "var Introduction" in t if t else False)
    if not script:
        return name, "No additional data available."

    script_text = script.string

    # Parse JavaScript variables
    introduction = re.search(r'var Introduction = "(.*?)";', script_text)
    experience = re.search(r'var Experience = (\[.*?\]);', script_text, re.DOTALL)
    publication = re.search(r'var Publication = (\[.*?\]);', script_text, re.DOTALL)

    # Clean and process data
    intro_text = introduction.group(1).replace("\\u003c", "<").replace("\\u003e", ">").replace("\\r\\n", "\n") if introduction else "No Introduction"
    experience_data = json.loads(experience.group(1)) if experience else []
    publication_data = json.loads(publication.group(1)) if publication else []

    details = f"Name: {name}\n\n"
    details += "--- Introduction ---\n" + BeautifulSoup(intro_text, "html.parser").get_text(separator="\n") + "\n\n"

    details += "--- Experience ---\n"
    for exp in experience_data:
        details += BeautifulSoup(exp["Experience"], "html.parser").get_text(separator="\n") + "\n\n"

    details += "--- Publications ---\n"
    for pub in publication_data:
        details += f"{pub.get('Author', 'Unknown Author')} - {pub.get('Journal', 'Unknown Journal')}\n"

    return name, details

def main():
    faculty_links = extract_faculty_links()

    if not faculty_links:
        print("No faculty links found.")
        return

    for url in faculty_links:
        try:
            name, details = parse_faculty_details(url)
            print(f"Scraping data for {name}...")
            pdf_file_name = os.path.join("Faculty_PDFs", f"{name}.pdf")
            save_to_pdf(pdf_file_name, details)
            print(f"Saved data for {name} to {pdf_file_name}")
        except Exception as e:
            print(f"Failed to process {url}: {e}")

if __name__ == "__main__":
    main()
