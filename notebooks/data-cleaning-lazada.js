import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import mysql from "mysql2/promise";
import dotenv from "dotenv";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.resolve(__dirname, "../.env") });

// Database connection configuration
const dbConfig = {
  host: process.env.DB_HOST,
  port: Number(process.env.DB_PORT),
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
  ssl: {
    mode: process.env.DB_SSL_MODE,
    ca: process.env.DB_SSL_CA,
  },
};

// Database connection variable
let dbConnection = null;

// Function to connect to database
async function connectToDatabase() {
  try {
    console.log("Connecting to MySQL database...");
    dbConnection = await mysql.createConnection(dbConfig);
    console.log("✅ Successfully connected to MySQL database!");
    return dbConnection;
  } catch (error) {
    console.error("❌ Failed to connect to database:", error.message);
    throw error;
  }
}

const lazada = JSON.parse(fs.readFileSync("../data.json", "utf8"));

// Function to parse sales string to numeric value
function parseSalesToNumber(salesString) {
  if (!salesString || typeof salesString !== 'string') {
    return 0;
  }

  try {
    // Remove "Terjual" and any whitespace
    let cleanString = salesString.replace(/Terjual/g, '').trim();

    // Check for "Rb" (Ribuan - Thousands in Indonesian)
    if (cleanString.includes('Rb')) {
      const numberPart = cleanString.replace('Rb', '').trim();
      const numberValue = parseFloat(numberPart);
      if (!isNaN(numberValue)) {
        return numberValue * 1000; // Convert to thousands
      }
    }

    // Check for "K" (Thousands)
    if (cleanString.toUpperCase().includes('K')) {
      const numberPart = cleanString.toUpperCase().replace('K', '').trim();
      const numberValue = parseFloat(numberPart);
      if (!isNaN(numberValue)) {
        return numberValue * 1000; // Convert to thousands
      }
    }

    // Check for "Jt" (Juta - Millions in Indonesian)
    if (cleanString.includes('Jt')) {
      const numberPart = cleanString.replace('Jt', '').trim();
      const numberValue = parseFloat(numberPart);
      if (!isNaN(numberValue)) {
        return numberValue * 1000000; // Convert to millions
      }
    }

    // Check for "M" (Millions)
    if (cleanString.toUpperCase().includes('M')) {
      const numberPart = cleanString.toUpperCase().replace('M', '').trim();
      const numberValue = parseFloat(numberPart);
      if (!isNaN(numberValue)) {
        return numberValue * 1000000; // Convert to millions
      }
    }

    // If no suffix found, try to parse as plain number
    const plainNumber = parseFloat(cleanString);
    if (!isNaN(plainNumber)) {
      return plainNumber;
    }

    return 0;
  } catch (error) {
    console.warn(`Warning: Could not parse sales value "${salesString}":`, error.message);
    return 0;
  }
}

let dataFinal = [];
function filterFeatureData() {
  const seenUrls = new Set(); // Track seen URLs to avoid duplicates
  const seenTitles = new Set(); // Track seen titles to avoid duplicates

  for (const data of lazada.data) {
    const formattedUrl = data.itemUrl.startsWith("//")
      ? "https:" + data.itemUrl
      : data.itemUrl;

    // Check if URL or title already exists
    if (!seenUrls.has(formattedUrl) && !seenTitles.has(data.itemTitle)) {
      seenUrls.add(formattedUrl);
      seenTitles.add(data.itemTitle);
      dataFinal.push({
        img: data.itemImg,
        title: data.itemTitle,
        discountPrice: data.itemDiscountPrice,
        sales: data.itemSales,
        salesNumeric: parseSalesToNumber(data.itemSales), // Add numeric sales value
        price: data.itemPromotionPrice,
        currency: data.currency,
        rating: data.itemRatingScore,
        url: formattedUrl,
      });
    }
  }

  console.log(`Total items: ${lazada.data.length}, Unique items: ${dataFinal.length}, Duplicates removed: ${lazada.data.length - dataFinal.length}`);

  // Show some examples of sales conversion
  console.log("📊 Sales conversion examples:");
  const examples = dataFinal.slice(0, 5);
  examples.forEach((item, index) => {
    console.log(`  ${index + 1}. "${item.sales}" → ${item.salesNumeric} units`);
  });
}

// Function to create lazada table
async function createLazadaTable() {
  try {
    console.log("📋 Creating lazada table...");

    // Drop existing table if it exists
    await dbConnection.execute("DROP TABLE IF EXISTS lazada");
    console.log("🗑️ Existing table dropped (if existed)");

    const createTableQuery = `
      CREATE TABLE lazada (
        id INT AUTO_INCREMENT PRIMARY KEY,
        img TEXT,
        title VARCHAR(500),
        discount_price VARCHAR(20),
        sales_original VARCHAR(100),
        sales_numeric DECIMAL(15, 2),
        price VARCHAR(20),
        currency VARCHAR(10),
        rating VARCHAR(20),
        url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_title (title(255)),
        INDEX idx_sales_numeric (sales_numeric)
      ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    `;

    await dbConnection.execute(createTableQuery);
    console.log("✅ Lazada table created successfully!");
  } catch (error) {
    console.error("❌ Error creating table:", error.message);
    throw error;
  }
}

// Function to insert data into lazada table
async function insertLazadaData() {
  try {
    console.log(`📝 Inserting ${dataFinal.length} items into lazada table...`);

    const insertQuery = `
      INSERT INTO lazada (img, title, discount_price, sales_original, sales_numeric, price, currency, rating, url)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `;

    let successCount = 0;
    let errorCount = 0;

    for (const item of dataFinal) {
      try {
        await dbConnection.execute(insertQuery, [
          item.img || null,
          item.title || null,
          item.discountPrice || null,
          item.sales || null,                          // Original sales string
          item.salesNumeric || 0,                      // Numeric sales value
          item.price || null,
          item.currency || 'IDR',
          item.rating || null,
          item.url || null
        ]);
        successCount++;

        // Progress indicator
        if (successCount % 50 === 0) {
          console.log(`  ➡️ Progress: ${successCount}/${dataFinal.length} items inserted`);
        }
      } catch (error) {
        errorCount++;
        console.error(`  ❌ Error inserting item "${item.title.substring(0, 50)}...":`, error.message);
      }
    }

    console.log(`✅ Data insertion completed: ${successCount} successful, ${errorCount} failed`);

    // Verify insertion
    const [countResult] = await dbConnection.execute('SELECT COUNT(*) as total FROM lazada');
    console.log(`📊 Total records in lazada table: ${countResult[0].total}`);

  } catch (error) {
    console.error("❌ Error inserting data:", error.message);
    throw error;
  }
}

// Main function to run the application
async function main() {
  try {
    // Connect to database
    await connectToDatabase();

    // Test the connection with a simple query
    const [rows] = await dbConnection.execute("SELECT 1 as test");
    console.log("🎯 Database test query successful:", rows[0]);

    // Create lazada table
    await createLazadaTable();

    // Process the Lazada data
    filterFeatureData();

    // Export dataFinal to JSON file
    fs.writeFileSync("../output.json", JSON.stringify(dataFinal, null, 2), "utf8");
    console.log("📁 Data exported to output.json");

    // Insert data into database
    await insertLazadaData();

    // Display some sample data from database
    const [sampleData] = await dbConnection.execute('SELECT * FROM lazada LIMIT 3');
    console.log("📋 Sample data from database:");
    console.table(sampleData);

  } catch (error) {
    console.error("💥 Error in main execution:", error);
  } finally {
    // Close the database connection
    if (dbConnection) {
      await dbConnection.end();
      console.log("🔌 Database connection closed");
    }
  }
}

// Run the main function
main();
