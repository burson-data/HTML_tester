import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO
import time
import re

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

def scrape_with_selenium(url, selector, click_selector=None):
    """
    Scrape menggunakan Selenium dengan Firefox untuk handle JavaScript dan dropdown
    """
    if not SELENIUM_AVAILABLE:
        return "Error: Selenium tidak terinstall"

    driver = None
    try:
        # Setup Firefox options
        firefox_options = Options()
        firefox_options.add_argument("--headless")
        firefox_options.add_argument("--no-sandbox")
        firefox_options.add_argument("--disable-dev-shm-usage")
        firefox_options.add_argument("--width=1920")
        firefox_options.add_argument("--height=1080")
        firefox_options.set_preference("general.useragent.override", 
                                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0")
        
        driver = webdriver.Firefox(options=firefox_options)
        driver.get(url)
        
        # Wait for page to load
        time.sleep(5)
        
        # Jika ada selector untuk diklik (dropdown button)
        if click_selector:
            try:
                # Wait for clickable element
                clickable_element = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, click_selector))
                )
                
                # Scroll ke element jika perlu
                driver.execute_script("arguments[0].scrollIntoView(true);", clickable_element)
                time.sleep(2)
                
                # Klik element
                driver.execute_script("arguments[0].click();", clickable_element)
                time.sleep(3)  # Wait for dropdown to open
                
            except TimeoutException:
                print(f"Timeout: Tidak dapat menemukan button dengan selector: {click_selector}")
            except Exception as e:
                print(f"Error clicking dropdown: {e}")
        
        # Coba beberapa strategi untuk menemukan elemen
        author_name = None
        
        # Strategi 1: Wait for target element
        try:
            wait = WebDriverWait(driver, 15)
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            author_name = element.text.strip()
        except TimeoutException:
            pass
        
        # Strategi 2: Coba tanpa wait jika strategi 1 gagal
        if not author_name:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    author_name = elements[0].text.strip()
            except NoSuchElementException:
                pass
        
        # Strategi 3: Coba selector alternatif untuk Kumparan
        if not author_name and 'kumparan.com' in url:
            alternative_selectors = [
                'span[data-qa-id="editor-name"]',
                '[data-qa-id="editor-name"]',
                '.editor-name',
                'span:contains("Muhammad")',
                'a[href*="/muhammad"]',
                'a[href*="author"]'
            ]
            
            for alt_selector in alternative_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, alt_selector)
                    if elements:
                        author_name = elements[0].text.strip()
                        if author_name:
                            break
                except:
                    continue
        
        # Strategi 4: Debug - ambil semua teks yang ada
        if not author_name:
            try:
                # Ambil semua span yang mungkin berisi nama
                spans = driver.find_elements(By.TAG_NAME, "span")
                for span in spans:
                    text = span.text.strip()
                    if text and len(text) > 5 and len(text) < 50:
                        # Cek apakah seperti nama (mengandung huruf kapital)
                        if any(c.isupper() for c in text) and not text.startswith('http'):
                            author_name = text
                            break
            except:
                pass
        
        driver.quit()
        
        return author_name if author_name else "Tidak ditemukan"
        
    except WebDriverException as e:
        if driver:
            driver.quit()
        return f"Error WebDriver: {str(e)[:100]}"
    except Exception as e:
        if driver:
            driver.quit()
        return f"Error: {str(e)[:100]}"

def scrape_author_from_url(url, html_tag, use_selenium=False, click_selector=None, max_retries=3):
    """
    Scrape author name from given URL using specified HTML tag
    """
    if use_selenium:
        return scrape_with_selenium(url, html_tag, click_selector)

    # Original BeautifulSoup method
    for attempt in range(max_retries):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            author_element = find_element_by_selector(soup, html_tag)
            
            if author_element:
                author_name = extract_author_text(author_element, html_tag)
                return author_name.strip() if author_name else "Tidak ditemukan"
            else:
                return "Tag tidak ditemukan"
                
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                return f"Error: {str(e)}"
            time.sleep(1)
        except Exception as e:
            return f"Error parsing: {str(e)}"

    return "Error: Gagal setelah beberapa percobaan"

def find_element_by_selector(soup, selector):
    """Find element using CSS selector or simple tag name"""
    try:
        if selector.lower().startswith('meta'):
            return soup.select_one(selector)
        elif '.' in selector or '#' in selector or '[' in selector:
            return soup.select_one(selector)
        else:
            return soup.find(selector)
    except Exception:
        return soup.find(selector)

def extract_author_text(element, selector):
    """Extract author text from element based on selector type"""
    if not element:
        return None
        
    if selector.lower().startswith('meta'):
        return element.get('content', '')
    elif '[data-' in selector.lower():
        attr_match = re.search(r'\[([^=\]]+)', selector)
        if attr_match:
            attr_name = attr_match.group(1)
            return element.get(attr_name, element.get_text())

    return element.get_text()

def main():
    st.set_page_config(
        page_title="News Author Scraper with Firefox",
        page_icon="📰",
        layout="wide"
    )

    st.title("📰 News Author Scraper (Firefox + Enhanced Error Handling)")
    st.markdown("Aplikasi untuk mengekstrak nama penulis berita dari multiple URL")

    # Sidebar for instructions
    with st.sidebar:
        st.header("📋 Panduan Penggunaan")
        st.markdown("""
        **Mode Scraping:**
        - **BeautifulSoup**: Untuk konten statis
        - **Firefox Selenium**: Untuk dropdown/JavaScript
        
        **Untuk Kumparan.com:**
        - HTML Tag: `span[data-qa-id="editor-name"]`
        - Atau coba: `[data-qa-id="editor-name"]`
        
        **Tips:**
        - Kosongkan Dropdown Button jika tidak tahu
        - Aplikasi akan mencoba beberapa strategi
        """)
        
        if not SELENIUM_AVAILABLE:
            st.warning("⚠️ Selenium tidak terinstall")

    # Main content
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🔗 Input URLs")
        urls_input = st.text_area(
            "Masukkan URLs (satu per baris):",
            height=150,
            placeholder="https://kumparan.com/kumparantech/article1"
        )
        
        st.subheader("⚙️ Scraping Settings")
        
        # Mode selection
        use_selenium = st.checkbox(
            "🦊 Gunakan Firefox Selenium",
            value=True,
            disabled=not SELENIUM_AVAILABLE
        )
        
        # HTML selectors
        html_tag = st.text_input(
            "HTML Tag:",
            value="span[data-qa-id='editor-name']",
            help="Selector untuk nama penulis"
        )
        
        click_selector = ""
        if use_selenium:
            click_selector = st.text_input(
                "Dropdown Button (opsional):",
                placeholder="Kosongkan jika tidak tahu",
                help="Button yang perlu diklik untuk membuka dropdown"
            )
        
        # Process button
        if st.button("🚀 Mulai Scraping", type="primary"):
            if urls_input and html_tag:
                urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
                
                if urls:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    results = []
                    
                    for i, url in enumerate(urls):
                        status_text.text(f"Processing {i+1}/{len(urls)}: {url[:50]}...")
                        
                        author = scrape_author_from_url(
                            url, 
                            html_tag, 
                            use_selenium=use_selenium,
                            click_selector=click_selector if click_selector else None
                        )
                        
                        results.append({
                            'No': i+1,
                            'URL': url,
                            'Author': author,
                            'Method': 'Firefox' if use_selenium else 'BeautifulSoup',
                            'Status': 'Success' if not author.startswith('Error') and author != 'Tidak ditemukan' else 'Failed'
                        })
                        
                        progress_bar.progress((i+1)/len(urls))
                        time.sleep(3 if use_selenium else 1)
                    
                    status_text.text("✅ Scraping selesai!")
                    st.session_state.results = results
                else:
                    st.error("Tidak ada URL yang valid!")
            else:
                st.error("Mohon isi URLs dan HTML tag!")

    with col2:
        st.subheader("📊 Results")
        
        if 'results' in st.session_state:
            df = pd.DataFrame(st.session_state.results)
            
            # Statistics
            total_urls = len(df)
            successful = len(df[df['Status'] == 'Success'])
            failed = total_urls - successful
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            col_stat1.metric("Total", total_urls)
            col_stat2.metric("Berhasil", successful)
            col_stat3.metric("Gagal", failed)
            
            # Results table
            st.dataframe(df, use_container_width=True)
            
            # Export to Excel
            if st.button("📥 Export to Excel"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Authors')
                
                output.seek(0)
                
                st.download_button(
                    label="⬇️ Download Excel",
                    data=output.getvalue(),
                    file_name=f"authors_{time.strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.info("Hasil akan muncul di sini")

if __name__ == "__main__":
    main()
