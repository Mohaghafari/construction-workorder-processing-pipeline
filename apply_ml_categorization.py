"""
Apply ML-based service categorization to BigQuery work orders
Routes to appropriate model based on company:
- AEON → AEON categorization (strict keyword matching)
- AE3 → AE3 categorization (semantic matching)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.oauth2 import service_account
from google.cloud import bigquery
import anthropic
import re
import time
import logging

# Import configuration
import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('modern_pipeline/categorization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize clients
credentials = service_account.Credentials.from_service_account_file(
    'modern_pipeline/credentials/service-account.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

bq_client = bigquery.Client(credentials=credentials, project='work-orders-435517')
anthropic_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

# Load prompts
with open("AE3-AEON Service Categorization Keywords/AeonPrompt.txt", "r", encoding='utf-8') as f:
    AEON_PROMPT = f.read()

with open("AE3-AEON Service Categorization Keywords/AE3 Prompt.txt", "r", encoding='utf-8') as f:
    AE3_PROMPT = f.read()

# Valid categories for each company
AEON_CATEGORIES = [
    "Straw Installation", "Straw Removal", 
    "Cleaning/loading sidewalk debris", "Hauling sidewalk debris", "Spreading Debris at Stockpile", "Cleaning/Loading Debris",
    "Excavate Infiltration", "Supply Material (Infiltration)", "Install Infiltration", 
    "Backfill Infiltration", "Compaction infiltration", "Relevel After Infiltration Backfill",
    "Initial Install of Slabs and Steps (Rear)", "Temporary Installation of Slabs and Steps (Front)", "Relevel Slabs",
    "Initial install of window wells",
    "Grading Work", "Topping Up Under Structures", "Filter Cloth Installation", 
    "Regrading washouts due to heavy rains", "Grade & Sod Contract Completions", "Extra Deep Sod (125 feet)", "Removing filter cloth from rear yard",
    "Loading & Hauling Topsoil/Fill Stockpile Within Site", "Spreading at Stockpile", "Leveling at Stockpile",
    "Loading & Hauling Topsoil/Fill from Lots to Stockpile", "Loading & Hauling Topsoil/Fill from Lot to Lot",
    "Spreading Topsoil on Lots", "Spreading Topsoil", "Loading & Hauling Topsoil/Fill from Stockpile to Lots",
    "Importing Topsoil/Fill From Offsite", "Topsoil Placement for In-Betweens", "Spreading/Topping Up In-Betweens", 
    "Removing Rocks & Debris from Topsoil",
    "Sod Removal", "Settlement Repairs", "Curb settlement repairs", "Sod Material for Curb Repair", 
    "Driveway Edge Settlement Repairs", "Sod Material for Driveway Edge",
    "Miscellaneous", "Bin Management", "Indoor Cleaning", "Garbage Collection", "Brick Management",
    "Concrete Work", "Equipment Supply", "Garage Filling & Leveling", "Labor Supply", "Road Maintenance",
    "Wall & Fence Installation", "Water Management", "Drainage System Installation", "Sod Installation"
]

AE3_CATEGORIES = [
    # LEVEL 1: Highly Specific Operations
    "Ripping Basement", "Ripping Sewers", "Ripping Base", "Ripping Backfill",
    "Stockpile Sewer", "Stockpile Basement", "Backfill Basement", "Sewer Backfill",
    "Sewer Excavation", "Basement Excavation", "Double Cast Sewer", "Double Cast Basement",
    "Straw Installation", "Straw Removal", "Strip Topsoil prior to Excavation", "Driveway Cut",
    # LEVEL 2: Moderately Specific Operations
    "Loading Fill From Lots", "Loading Fill To Lots", "Haul From Stockpile", "Haul To Stockpile",
    "Loading Excess Fill Offsite", "Hauling Excess Fill Offsite", "Spreading At Stockpile",
    "Rough Grade", "Low Lots", "Base Condition", "Concrete Work", "Mud",
    # LEVEL 3: General Operations
    "General Stockpile", "Grade", "Releveling", "Spreading/Top Up",
    "Cast/ Double Cast", "General Straw", "Road", "Tarp", "Flagman", "Snow", "Ramp",
    # Default Case
    "Miscellaneous"
]

def categorize_aeon(description):
    """Categorize AEON work orders using strict keyword matching"""
    try:
        enhanced_prompt = f"{AEON_PROMPT}\n\nRemember: ONLY use the exact category names from the provided service categories list. DO NOT create new categories that are not in the list. If no category matches exactly, use 'Miscellaneous'.\n\nInput: {description}"
        
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            temperature=0,
            messages=[{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": enhanced_prompt
                }]
            }]
        )
        
        result = response.content[0].text
        
        # Split into service blocks
        service_blocks = re.split(r'\n\n(?=Service:)', result.strip())
        
        # Process each service block
        parsed_services = []
        for block in service_blocks:
            service_match = re.search(r'Service:\s*(.*?)(?:\n|$)', block)
            blocks_match = re.search(r'Blocks/Lots/Units:\s*(.*?)(?:\n|$)', block)
            
            if service_match:
                service = service_match.group(1).strip()
                # Validate against AEON categories
                if not service.startswith("Settlement Repairs") and not service.startswith("Miscellaneous") and service not in AEON_CATEGORIES:
                    service = f"Miscellaneous ({service})"
                
                blocks = blocks_match.group(1).strip() if blocks_match else "Not specified"
                parsed_services.append((service, blocks))
        
        # Consolidate services (keep Settlement Repairs separate)
        consolidated_services = {}
        for service, blocks in parsed_services:
            if service.startswith("Settlement Repairs"):
                if service not in consolidated_services:
                    consolidated_services[service] = blocks
                else:
                    count = 1
                    while f"Settlement Repairs{count}" in consolidated_services:
                        count += 1
                    consolidated_services[f"Settlement Repairs{count}"] = blocks
            else:
                if service in consolidated_services:
                    if blocks != "Not specified" and consolidated_services[service] != "Not specified":
                        if blocks not in consolidated_services[service]:
                            consolidated_services[service] = f"{consolidated_services[service]}, {blocks}"
                    elif blocks != "Not specified":
                        consolidated_services[service] = blocks
                else:
                    consolidated_services[service] = blocks
        
        # Format output
        formatted_services = []
        for service, blocks in consolidated_services.items():
            formatted_services.append(f"Service: {service}\nBlocks/Lots/Units: {blocks}")
        
        return "\n\n".join(formatted_services) if formatted_services else "Error in categorization"
        
    except Exception as e:
        logger.error(f"Error in AEON categorization: {e}")
        return f"Error in categorization: {str(e)}"

def categorize_ae3(description):
    """Categorize AE3 work orders using semantic matching"""
    try:
        enhanced_prompt = f"{AE3_PROMPT}\n\nRemember: Use semantic understanding to match descriptions to appropriate categories. Consider the intent and meaning of the description, not just exact keywords. Make reasonable associations between similar concepts (e.g., 'removing debris' can match 'Loading Excess Fill Offsite'). Only use 'Miscellaneous' when no category reasonably fits the description's intent.\n\nInput: {description}"
        
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            temperature=0,
            messages=[{
                "role": "user",
                "content": enhanced_prompt
            }]
        )
        
        result = response.content[0].text
        
        # Split into service blocks
        service_blocks = re.split(r'\n\n(?=Service:)', result.strip())
        
        # Process each service block
        parsed_services = []
        for block in service_blocks:
            service_match = re.search(r'Service:\s*(.*?)(?:\n|$)', block)
            blocks_match = re.search(r'Blocks/Lots/Units:\s*(.*?)(?:\n|$)', block)
            
            if service_match:
                service = service_match.group(1).strip()
                
                # Apply AE3 substitution rules
                if service == "Haul From Lots":
                    service = "Haul To Stockpile"
                elif service == "Haul To Lots":
                    service = "Haul From Stockpile"
                elif service == "Loading Fill To Stockpile":
                    service = "Loading Fill From Lots"
                elif service == "Loading Fill From Stockpile":
                    service = "Loading Fill To Lots"
                
                # Validate against AE3 categories
                if not service.startswith("Miscellaneous") and service not in AE3_CATEGORIES:
                    service = f"Miscellaneous ({service})"
                
                blocks = blocks_match.group(1).strip() if blocks_match else "Not specified"
                parsed_services.append((service, blocks))
        
        # Consolidate services
        consolidated_services = {}
        for service, blocks in parsed_services:
            if service in consolidated_services:
                if blocks != "Not specified" and consolidated_services[service] != "Not specified":
                    if blocks not in consolidated_services[service]:
                        consolidated_services[service] = f"{consolidated_services[service]}, {blocks}"
                elif blocks != "Not specified":
                    consolidated_services[service] = blocks
            else:
                consolidated_services[service] = blocks
        
        # Format output
        formatted_services = []
        for service, blocks in consolidated_services.items():
            formatted_services.append(f"Service: {service}\nBlocks/Lots/Units: {blocks}")
        
        return "\n\n".join(formatted_services) if formatted_services else "Error in categorization"
        
    except Exception as e:
        logger.error(f"Error in AE3 categorization: {e}")
        return f"Error in categorization: {str(e)}"

def apply_ml_categorization():
    """Apply ML categorization to all work orders in BigQuery"""
    logger.info("=== Starting ML Categorization Process ===")
    
    # Read work orders from corrected table
    query = """
        SELECT 
            work_order_id,
            description,
            company_name_standardized
        FROM `work-orders-435517.work_orders_production.raw_work_orders_corrected`
        WHERE description IS NOT NULL
        ORDER BY work_order_id
    """
    
    logger.info("Reading work orders from BigQuery...")
    df = bq_client.query(query).to_dataframe()
    logger.info(f"Loaded {len(df)} rows for categorization")
    
    # Process each work order
    categorized_data = []
    
    for idx, row in df.iterrows():
        work_order_id = row['work_order_id']
        description = row['description']
        company = row['company_name_standardized']
        
        logger.info(f"Processing {idx + 1}/{len(df)}: WO {work_order_id} - Company: {company}")
        
        # Route to appropriate categorizer
        if company == "Aeon Landscaping":
            categorization = categorize_aeon(description)
            logger.info(f"  → AEON categorization: {categorization[:100]}...")
        elif company == "AE3 Excavating":
            categorization = categorize_ae3(description)
            logger.info(f"  → AE3 categorization: {categorization[:100]}...")
        else:
            categorization = f"Service: Miscellaneous (No categorizer for {company})\nBlocks/Lots/Units: Not specified"
            logger.info(f"  → No categorizer for company: {company}")
        
        categorized_data.append({
            'work_order_id': work_order_id,
            'ml_categorization': categorization
        })
        
        # Rate limiting
        time.sleep(1)
        
        # Batch update every 5 rows
        if (idx + 1) % 5 == 0:
            logger.info(f"Batch update: saving categorizations for rows {idx - 3} to {idx + 1}")
            for data in categorized_data[-5:]:
                update_query = f"""
                    UPDATE `work-orders-435517.work_orders_production.raw_work_orders_corrected`
                    SET ml_categorization = '''{data['ml_categorization'].replace("'", "''")}'''
                    WHERE work_order_id = '{data['work_order_id']}'
                """
                try:
                    bq_client.query(update_query).result()
                except Exception as e:
                    logger.error(f"Error updating row {data['work_order_id']}: {e}")
                    # If streaming buffer issue, we'll create a new table
                    if "streaming buffer" in str(e).lower():
                        logger.info("Streaming buffer detected, will create new table at end...")
                        break
    
    logger.info("=== ML Categorization Complete ===")
    logger.info(f"Categorized {len(categorized_data)} work orders")
    
    # Save to new table (because of streaming buffer limitation)
    logger.info("Creating new table with categorizations...")
    
    create_table_query = """
        CREATE OR REPLACE TABLE `work-orders-435517.work_orders_production.raw_work_orders_with_ml` AS
        SELECT 
            c.*
        FROM `work-orders-435517.work_orders_production.raw_work_orders_corrected` c
    """
    bq_client.query(create_table_query).result()
    logger.info("Created base table, now adding ML categorizations...")
    
    # Add ML categorization column
    alter_query = """
        ALTER TABLE `work-orders-435517.work_orders_production.raw_work_orders_with_ml`
        ADD COLUMN IF NOT EXISTS ml_categorization STRING
    """
    try:
        bq_client.query(alter_query).result()
    except:
        pass  # Column might already exist
    
    # Insert categorizations using MERGE (works around streaming buffer)
    for data in categorized_data:
        merge_query = f"""
            MERGE `work-orders-435517.work_orders_production.raw_work_orders_with_ml` T
            USING (SELECT 
                '{data['work_order_id']}' as work_order_id,
                '''{data['ml_categorization'].replace("'", "''")}''' as ml_categorization
            ) S
            ON T.work_order_id = S.work_order_id
            WHEN MATCHED THEN
                UPDATE SET ml_categorization = S.ml_categorization
        """
        try:
            bq_client.query(merge_query).result()
        except Exception as e:
            logger.error(f"Error merging row {data['work_order_id']}: {e}")
    
    logger.info("✅ All categorizations saved!")
    
    # Show sample
    sample_query = """
        SELECT work_order_id, company_name_standardized, ml_categorization 
        FROM `work-orders-435517.work_orders_production.raw_work_orders_with_ml`
        WHERE ml_categorization IS NOT NULL
        LIMIT 3
    """
    logger.info("\nSample categorizations:")
    results = bq_client.query(sample_query).result()
    for row in results:
        logger.info(f"\nWO: {row['work_order_id']}")
        logger.info(f"Company: {row['company_name_standardized']}")
        logger.info(f"Categorization:\n{row['ml_categorization']}\n")

if __name__ == "__main__":
    apply_ml_categorization()

