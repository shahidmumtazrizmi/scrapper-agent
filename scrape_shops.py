import asyncio
import pandas as pd
import json
import os
import re
import requests

output_dir = "Top_Shops/best_selling_products_images"
logo_dir = "Top_Shops/shop_logo"
trend_dir = "Top_Shops/trend_images"
os.makedirs(output_dir, exist_ok=True)
os.makedirs(logo_dir, exist_ok=True)
os.makedirs(trend_dir, exist_ok=True)

async def extract_shop_data(page):
    print("Clicking 'Shop' link inside #page_header_left...")
    await page.click("#page_header_left >> text=Shop")

    print("Waiting for shop data to load...")
    await page.wait_for_selector(".ant-table-row", timeout=10000)

    rows = await page.query_selector_all(".ant-table-row")

    all_shops = []
    all_product_names = []
    all_product_prices = []
    image_counter = 1
    logo_counter = 1
    trend_counter = 1

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.kalodata.com"
    }

    for index, row in enumerate(rows):
        # ✅ Shop Logo
        logo_el = await row.query_selector("div.Component-Image.w-\\[56px\\].h-\\[56px\\].w-\\[56px\\].h-\\[56px\\]")
        shop_logo_filename = "N/A"
        if logo_el:
            style = await logo_el.get_attribute("style")
            match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
            if match:
                logo_url = match.group(1)
                try:
                    response = requests.get(logo_url, headers=headers)
                    if response.status_code == 200:
                        shop_logo_filename = f"shop_logo_{logo_counter}.png"
                        with open(os.path.join(logo_dir, shop_logo_filename), "wb") as f:
                            f.write(response.content)
                        print(f"✅ Saved shop logo {shop_logo_filename}")
                        logo_counter += 1
                    else:
                        print(f"❌ Failed to download shop logo (status {response.status_code})")
                except Exception as e:
                    print(f"❌ Error downloading logo {logo_url}: {e}")

        # Shop Name
        shop_name_el = await row.query_selector("div.line-clamp-1:not(.text-base-999)")
        shop_name = await shop_name_el.inner_text() if shop_name_el else "N/A"

        # Shop Type
        type_el = await row.query_selector("div.text-base-999.line-clamp-1")
        type_text = await type_el.inner_text() if type_el else "N/A"

        # Revenue
        rev_el = await row.query_selector("td.ant-table-cell.ant-table-column-sort")
        rev_text = await rev_el.inner_text() if rev_el else "N/A"

        # All TDs (for trend screenshots)
        td_elements = await row.query_selector_all("td")

        # Average Unit Price (last td)
        avg_unitp_text = await td_elements[-1].inner_text() if td_elements else "N/A"

        # Revenue Trend Screenshot (5th td)
        revenue_trend_filename = "N/A"
        if len(td_elements) > 4:
            try:
                revenue_trend_filename = f"revenue_trend_{trend_counter}.png"
                await td_elements[4].screenshot(path=os.path.join(trend_dir, revenue_trend_filename))
                print(f"✅ Screenshot saved for revenue trend: {revenue_trend_filename}")
            except Exception as e:
                print(f"❌ Error capturing screenshot for revenue trend: {e}")

        # Best Seller Images
        best_seller_images = []
        image_divs = await row.query_selector_all("div.Component-Image.cover.cover")
        for image_div in image_divs:
            await image_div.hover()
            await asyncio.sleep(1)

            # Image URL
            style = await image_div.get_attribute("style")
            match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
            if match:
                url = match.group(1)
                try:
                    response = requests.get(url, headers=headers)
                    if response.status_code == 200:
                        image_name = f"shop_{index+1}_image_{image_counter}.png"
                        image_path = os.path.join(output_dir, image_name)
                        with open(image_path, "wb") as f:
                            f.write(response.content)
                        best_seller_images.append(image_name)
                        print(f"✅ Saved {image_name}")
                        image_counter += 1
                    else:
                        print(f"❌ Failed to download image (status {response.status_code})")
                except Exception as e:
                    print(f"❌ Error downloading {url}: {e}")

        # Best Seller Product Names (collected like a shared pool)
        product_elements = await page.query_selector_all("span.line-clamp-2")
        for p in product_elements:
            product_name = await p.inner_text()
            normalized_product_name = ' '.join(product_name.split())
            if normalized_product_name not in all_product_names:
                all_product_names.append(normalized_product_name)
        all_product_prices = []
        # Best Seller Prices (similarly, as shared pool)
        price_elements = await page.query_selector_all("div.text-\\[16px\\].min-w-\\[80px\\].h-\\[20px\\].font-medium.bg-white")
        for el in price_elements:
            price_text = await el.inner_text()
            # normalized_price = ' '.join(price_text.split())
            # if normalized_price not in all_product_prices:
            all_product_prices.append(price_text)
        
        for el in all_product_prices:
            print(f"Price: {el}")
            

        shop_data = {
            "Rank": index + 1,
            "Shop Logo": shop_logo_filename,
            "Name": shop_name,
            "Type": type_text,
            "Best Sellers": [],  # filled later
            "Best Seller Prices": [],  # filled later
            "Best Seller Images": best_seller_images,
            "Revenue": rev_text,
            "Revenue Trend": revenue_trend_filename,
            "Average Unit Price": avg_unitp_text
        }

        all_shops.append(shop_data)
        trend_counter += 1

    # Slice product names and prices per shop using best seller images as reference
    product_idx = 0
    for shop in all_shops:
        num_images = len(shop["Best Seller Images"])
        shop["Best Sellers"] = all_product_names[product_idx:product_idx + num_images]
        # shop["Best Seller Prices"] = all_product_prices[product_idx:product_idx + num_images]
        product_idx += num_images
    
    # Assign Best Seller Prices based on Best Sellers
    price_idx = 0
    for shop in all_shops:
        num_products = len(shop["Best Sellers"])
        shop["Best Seller Prices"] = all_product_prices[price_idx:price_idx + num_products]
        price_idx += num_products

    # Display results
    for i, shop in enumerate(all_shops):
        print(f"\nShop {i + 1}:")
        for k, v in shop.items():
            print(f"  {k}: {v if not isinstance(v, list) else ', '.join(v)}")

    # Save to CSV
    df = pd.DataFrame(all_shops)
    df["Best Sellers"] = df["Best Sellers"].apply(lambda x: ', '.join(x))
    df["Best Seller Prices"] = df["Best Seller Prices"].apply(lambda x: ', '.join(x))
    df["Best Seller Images"] = df["Best Seller Images"].apply(lambda x: ', '.join(x))
    df.to_csv("Top_Shops/top_shops_output.csv", index=False)

    # Save to JSON
    with open("Top_Shops/top_shops_output.json", "w", encoding="utf-8") as f:
        json.dump(all_shops, f, ensure_ascii=False, indent=4)
