import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO
import time
import re


SELENIUM_AVAILABLE = True

def scrape_with_selenium(url, selectors, click_selector=None):
    """
    Scrape menggunakan Selenium dengan Firefox untuk handle JavaScript dan dropdown
    """
    if not SELENIUM_AVAILABLE:
        return ["Error: Selenium tidak terinstall"] * len(selectors)

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
                clickable_element = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, click_selector))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", clickable_element)
                time.sleep(2)
                driver.execute_script("arguments[0].click();", clickable_element)
                time.sleep(3)
            except TimeoutException:
                print(f"Timeout: Tidak dapat menemukan button dengan selector: {click_selector}")
            except Exception as e:
                print(f"Error clicking dropdown: {e}")
        
        results = []
        
        # Scrape untuk setiap selector
        for selector in selectors:
            if not selector.strip():
                results.append("Selector kosong")
                continue
                
            found_text = None
            
            # Strategi 1: Wait for target element
            try:
                wait = WebDriverWait(driver, 15)
                element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                found_text = element.text.strip()
            except TimeoutException:
                pass
            
            # Strategi 2: Coba tanpa wait jika strategi 1 gagal
            if not found_text:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        found_text = elements[0].text.strip()
                except NoSuchElementException:
                    pass
            
            # Strategi 3: Coba selector alternatif untuk Kumparan
            if not found_text and 'kumparan.com' in url:
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
                            found_text = elements[0].text.strip()
                            if found_text:
                                break
                    except:
                        continue
            
            results.append(found_text if found_text else "Tidak ditemukan")
        
        driver.quit()
        return results
        
    except WebDriverException as e:
        if driver:
            driver.quit()
        return [f"Error WebDriver: {str(e)[:100]}"] * len(selectors)
    except Exception as e:
        if driver:
            driver.quit()
        return [f"Error: {str(e)[:100]}"] * len(selectors)

def scrape_author_from_url(url, html_tags, use_selenium=False, click_selector=None, max_retries=3):
    """
    Scrape content from given URL using specified HTML tags
    """
    if use_selenium:
        return scrape_with_selenium(url, html_tags, click_selector)

    # Original BeautifulSoup method
    results = []

    for attempt in range(max_retries):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for html_tag in html_tags:
                if not html_tag.strip():
                    results.append("Selector kosong")
                    continue
                    
                element = find_element_by_selector(soup, html_tag)
                
                if element:
                    content = extract_author_text(element, html_tag)
                    results.append(content.strip() if content else "Tidak ditemukan")
                else:
                    results.append("Tag tidak ditemukan")
            
            return results
                
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                return [f"Error: {str(e)}"] * len(html_tags)
            time.sleep(1)
        except Exception as e:
            return [f"Error parsing: {str(e)}"] * len(html_tags)

    return ["Error: Gagal setelah beberapa percobaan"] * len(html_tags)

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
    """Extract text from element based on selector type"""
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
        page_title="Multi-Tag Web Scraper",
        page_icon="🔍",
        layout="wide"
    )

    st.title("🔍 Multi-Tag Web Scraper (Hingga 5 Tag HTML)")
    st.markdown("Aplikasi untuk mengekstrak konten dari multiple URL menggunakan multiple HTML tag")

    # Sidebar for instructions
    with st.sidebar:
        st.header("📋 Panduan Penggunaan")
        st.markdown("""
        **Fitur Baru:**
        - ✅ Hingga 5 tag HTML sekaligus
        - ✅ Input multiple URLs (unlimited)
        - ✅ Export hasil ke Excel
        
        **Mode Scraping:**
        - **BeautifulSoup**: Untuk konten statis
        - **Firefox Selenium**: Untuk dropdown/JavaScript
        
        **Contoh Tag HTML:**
        - `span[data-qa-id="editor-name"]`
        - `meta[name="author"]`
        - `.author-name`
        - `#author-id`
        - `h1.title`
        """)
        
        if not SELENIUM_AVAILABLE:
            st.warning("⚠️ Selenium tidak terinstall")

    # Main content
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🔗 Input URLs")
        urls_input = st.text_area(
            "Masukkan URLs (satu per baris, unlimited):",
            height=200,
            placeholder="""https://example.com/article1
    https://example.com/article2
    https://example.com/article3
    ...dan seterusnya"""
        )
        
        # URL count display
        if urls_input:
            url_count = len([url for url in urls_input.split('\n') if url.strip()])
            st.info(f"📊 Total URLs: {url_count}")
        
        st.subheader("⚙️ Scraping Settings")
        
        # Mode selection
        use_selenium = st.checkbox(
            "🦊 Gunakan Firefox Selenium",
            value=True,
            disabled=not SELENIUM_AVAILABLE
        )
        
        # HTML selectors (up to 5)
        st.markdown("**HTML Tags (Maksimal 5):**")
        html_tags = []
        
        tag_labels = ["Tag HTML 1", "Tag HTML 2", "Tag HTML 3", "Tag HTML 4", "Tag HTML 5"]
        default_values = [
            "span[data-qa-id='editor-name']",
            "meta[name='author']",
            ".author-name",
            "h1",
            ""
        ]
        
        for i in range(5):
            tag = st.text_input(
                f"{tag_labels[i]}:",
                value=default_values[i] if i < len(default_values) else "",
                key=f"tag_{i}",
                help=f"CSS selector untuk elemen {i+1}"
            )
            html_tags.append(tag)
        
        # Filter out empty tags
        active_tags = [tag for tag in html_tags if tag.strip()]
        
        if active_tags:
            st.success(f"✅ {len(active_tags)} tag aktif")
        else:
            st.warning("⚠️ Minimal 1 tag HTML harus diisi")
        
        click_selector = ""
        if use_selenium:
            click_selector = st.text_input(
                "Dropdown Button (opsional):",
                placeholder="Kosongkan jika tidak tahu",
                help="Button yang perlu diklik untuk membuka dropdown"
            )
        
        # Process button
        if st.button("🚀 Mulai Scraping", type="primary"):
            if urls_input and active_tags:
                urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
                
                if urls:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    results = []
                    
                    for i, url in enumerate(urls):
                        status_text.text(f"Processing {i+1}/{len(urls)}: {url[:50]}...")
                        
                        scraped_data = scrape_author_from_url(
                            url, 
                            active_tags, 
                            use_selenium=use_selenium,
                            click_selector=click_selector if click_selector else None
                        )
                        
                        # Create result row
                        result_row = {
                            'No': i+1,
                            'URL': url,
                            'Method': 'Firefox' if use_selenium else 'BeautifulSoup'
                        }
                        
                        # Add results for each tag
                        for j, tag in enumerate(active_tags):
                            result_row[f'Tag_{j+1}_Result'] = scraped_data[j] if j < len(scraped_data) else "Error"
                            result_row[f'Tag_{j+1}_Selector'] = tag
                        
                        # Determine overall status
                        has_success = any(
                            not result.startswith('Error') and result != 'Tidak ditemukan' and result != 'Tag tidak ditemukan'
                            for result in scraped_data
                        )
                        result_row['Status'] = 'Success' if has_success else 'Failed'
                        
                        results.append(result_row)
                        
                        progress_bar.progress((i+1)/len(urls))
                        time.sleep(3 if use_selenium else 1)
                    
                    status_text.text("✅ Scraping selesai!")
                    st.session_state.results = results
                    st.session_state.active_tags = active_tags
                else:
                    st.error("Tidak ada URL yang valid!")
            else:
                st.error("Mohon isi URLs dan minimal 1 HTML tag!")

    with col2:
        st.subheader("📊 Results")
        
        if 'results' in st.session_state:
            df = pd.DataFrame(st.session_state.results)
            
            # Statistics
            total_urls = len(df)
            successful = len(df[df['Status'] == 'Success'])
            failed = total_urls - successful
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            col_stat1.metric("Total URLs", total_urls)
            col_stat2.metric("Berhasil", successful)
            col_stat3.metric("Gagal", failed)
            
            # Show active tags info
            if 'active_tags' in st.session_state:
                st.info(f"🏷️ Tag aktif: {len(st.session_state.active_tags)}")
                with st.expander("Lihat Tag yang Digunakan"):
                    for i, tag in enumerate(st.session_state.active_tags, 1):
                        st.code(f"Tag {i}: {tag}")
            
            # Results table with better formatting
            st.markdown("### 📋 Detail Hasil")
            
            # Create a more readable dataframe
            display_df = df[['No', 'URL', 'Method', 'Status']].copy()
            
            # Add tag results in a more readable format
            for i in range(len(st.session_state.active_tags)):
                if f'Tag_{i+1}_Result' in df.columns:
                    display_df[f'Tag {i+1}'] = df[f'Tag_{i+1}_Result']
            
            st.dataframe(display_df, use_container_width=True)
            
            # Export to Excel
            if st.button("📥 Export to Excel"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # Main results
                    df.to_excel(writer, index=False, sheet_name='Results')
                    
                    # Summary sheet
                    summary_data = {
                        'Metric': ['Total URLs', 'Successful', 'Failed', 'Success Rate'],
                        'Value': [total_urls, successful, failed, f"{(successful/total_urls*100):.1f}%"]
                    }
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, index=False, sheet_name='Summary')
                    
                    # Tags info sheet
                    if 'active_tags' in st.session_state:
                        tags_data = {
                            'Tag_Number': [f"Tag {i+1}" for i in range(len(st.session_state.active_tags))],
                            'Selector': st.session_state.active_tags
                        }
                        tags_df = pd.DataFrame(tags_data)
                        tags_df.to_excel(writer, index=False, sheet_name='Tags_Used')
                
                output.seek(0)
                
                st.download_button(
                    label="⬇️ Download Excel File",
                    data=output.getvalue(),
                    file_name=f"scraping_results_{time.strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.info("Hasil akan muncul di sini setelah scraping")
            st.markdown("""
            **Yang akan ditampilkan:**
            - 📊 Statistik scraping
            - 📋 Tabel hasil detail
            - 📥 Tombol export Excel
            - 🏷️ Info tag yang digunakan
            """)

if __name__ == "__main__":
    main()
