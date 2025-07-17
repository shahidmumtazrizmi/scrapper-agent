import asyncio
import pandas as pd
import json
import os
import re
import requests
import logging

Shop_dir = "Top_Categories"
if not os.path.exists(Shop_dir):
    os.makedirs(Shop_dir)

log_file_path = "Top_Categories/Top_Categories.log"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", handlers=[
    logging.FileHandler(log_file_path),
    logging.StreamHandler()
])

output_dir = "Top_Category/best_selling_products_images"
logo_dir = "Top_Category/category_logo"
trend_dir = "Top_Category/trend_images"
os.makedirs(output_dir, exist_ok=True)
os.makedirs(logo_dir, exist_ok=True)
os.makedirs(trend_dir, exist_ok=True)

async def extract_category_data(page):
    logging.info("Clicking 'category' link inside #page_header_left...")
    await page.click("#page_header_left >> text=Category")

    logging.info("Waiting for category data to load...")
    await page.wait_for_selector(".ant-table-row.ant-table-row-level-0", timeout=10000)

    rows = await page.query_selector_all(".ant-table-row.ant-table-row-level-0")

    all_Category = []
    all_product_names = []
    image_counter = 1
    logo_counter = 1
    trend_counter = 1

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.kalodata.com"
    }

    for index, row in enumerate(rows):
        # ✅ Creator Logo
        logo_el = await row.query_selector("div.Component-Image.round.w-\\[56px\\].h-\\[56px\\].w-\\[56px\\].h-\\[56px\\]")
        category_logo_filename = "N/A"
        if logo_el:
            style = await logo_el.get_attribute("style")
            match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
            if match:
                logo_url = match.group(1)
                try:
                    response = requests.get(logo_url, headers=headers)
                    if response.status_code == 200:
                        category_logo_filename = f"category_logo_{logo_counter}.png"
                        with open(os.path.join(logo_dir, category_logo_filename), "wb") as f:
                            f.write(response.content)
                        logging.info(f"Saved logo {category_logo_filename}")
                        logo_counter += 1
                    else:
                        logging.info(f"Failed to download logo image (status {response.status_code})")
                except Exception as e:
                    logging.error(f"Error downloading logo {logo_url}: {e}")

        # Creator Profile
        category_name_el = await row.query_selector("div.line-clamp-1:not(.text-base-999)")
        category_name = await category_name_el.inner_text() if category_name_el else "N/A"

        # Creator Name
        type_el = await row.query_selector("div.text-base-999.line-clamp-1")
        type_text = await type_el.inner_text() if type_el else "N/A"

        # Best Sellers (hover and extract image)
        image_divs = await row.query_selector_all("div.Component-Image.cover.cover")
        best_seller_images = []

        for image_div in image_divs:
            await image_div.hover()
            await asyncio.sleep(1)

            style = await image_div.get_attribute("style")
            match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
            if match:
                url = match.group(1)
                try:
                    response = requests.get(url, headers=headers)
                    if response.status_code == 200:
                        image_name = f"category_{index+1}_image_{image_counter}.png"
                        image_path = os.path.join(output_dir, image_name)
                        with open(image_path, "wb") as f:
                            f.write(response.content)
                        best_seller_images.append(image_name)
                        logging.info(f"Saved {image_name}")
                        image_counter += 1
                    else:
                        logging.info(f"Failed to download image (status {response.status_code})")
                except Exception as e:
                    logging.error(f"Error downloading {url}: {e}")

        product_elements = await page.query_selector_all("span.line-clamp-2")
        for p in product_elements:
            product_name = await p.inner_text()
            normalized_product_name = ' '.join(product_name.split())

            if normalized_product_name not in all_product_names:
                all_product_names.append(normalized_product_name)

        td_elements = await row.query_selector_all("td")
        # Revenue
        rev_el = await row.query_selector("td.ant-table-cell.ant-table-column-sort")
        rev_text = await rev_el.inner_text() if rev_el else "N/A"
        # Followers
        followers = await td_elements[2].inner_text() if len(td_elements) > 2 else "N/A"
        # Content Views
        content_views = await td_elements[6].inner_text() if len(td_elements) > 6 else "N/A"

        # Revenue Trend Screenshot (5th td)
        revenue_trend_filename = "N/A"
        if len(td_elements) > 5:
            try:
                revenue_trend_filename = f"revenue_trend_{trend_counter}.png"
                await td_elements[5].screenshot(path=os.path.join(trend_dir, revenue_trend_filename))
                logging.info(f"Screenshot saved for revenue trend: {revenue_trend_filename}")
            except Exception as e:
                logging.error(f"Error capturing screenshot for revenue trend: {e}")

        # Views Trend Screenshot (7th td)
        views_trend_filename = "N/A"
        if len(td_elements) > 7:
            try:
                views_trend_filename = f"views_trend_{trend_counter}.png"
                await td_elements[7].screenshot(path=os.path.join(trend_dir, views_trend_filename))
                logging.info(f"Screenshot saved for views trend: {views_trend_filename}")
            except Exception as e:
                logging.error(f"Error capturing screenshot for views trend: {e}")

        trend_counter += 1

        # Creator Debut Time
        debut_time_el = await row.query_selector("span.Component-MemberText")
        debut_time = await debut_time_el.inner_text() if debut_time_el else "N/A"

        category_data = {
            "Rank": index + 1,
            "Creator Logo": category_logo_filename,
            "Creator Profile": category_name,
            "Creator Name": type_text,
            "Followers": followers,
            "Best Sellers": [],
            "Best Seller Images": best_seller_images,
            "Revenue": rev_text,
            "Revenue Trend": revenue_trend_filename,
            "Content Views": content_views,
            "Views Trend": views_trend_filename,
            "Creator Debut Time": debut_time
        }

        all_Category.append(category_data)

    for i in range(len(all_Category)):
        start = i * 3
        end = start + 3
        all_Category[i]["Best Sellers"] = all_product_names[start:end]

    # Display results
    for i, category in enumerate(all_Category):
        logging.info(f"\nCreator {i + 1}:")
        for k, v in category.items():
            logging.info(f"  {k}: {v}")

    # Save to CSV
    df = pd.DataFrame(all_Category)
    df["Best Sellers"] = df["Best Sellers"].apply(lambda x: ', '.join(x))
    df["Best Seller Images"] = df["Best Seller Images"].apply(lambda x: ', '.join(x))
    df.to_csv("Top_Category/top_Category_output.csv", index=False)

    # Save to JSON
    with open("Top_Category/top_Category_output.json", "w", encoding="utf-8") as f:
        json.dump(all_Category, f, ensure_ascii=False, indent=4)
