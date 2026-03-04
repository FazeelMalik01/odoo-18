/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { unaccent } from "@web/core/utils/strings";
import { reactive } from "@odoo/owl";

patch(ProductScreen.prototype, {
    setup() {
        super.setup();
        // Track packaging matches for products found via packaging barcode search
        this.packagingMatches = new Map(); // product_id -> packaging object
    },
    /**
     * Override loadProductFromDBDomain to include packaging barcode search in the domain
     * This is more efficient than searching separately
     */
    loadProductFromDBDomain(searchProductWord) {
        const baseDomain = super.loadProductFromDBDomain(searchProductWord);
        
        // We can't directly search packaging barcodes in the domain,
        // so we'll handle it in loadProductFromDB instead
        return baseDomain;
    },

    /**
     * Override loadProductFromDB to also search for packaging barcodes
     * This extends the database search to include products with matching packaging barcodes
     */
    async loadProductFromDB() {
        const { searchProductWord } = this.pos;
        if (!searchProductWord) {
            return super.loadProductFromDB();
        }

        // First, call the original method to get standard results
        const standardResults = await super.loadProductFromDB();
        
        // Also search for products by packaging barcode
        // We need to search packaging model and then get the associated products
        try {
            // Try to get package_type_id field - it might have different names
            const packagingFields = ["product_id", "barcode", "name", "qty"];
            // Add package_type_id if available (try different possible field names)
            const possibleTypeFields = ["package_type_id", "packaging_type_id", "package_type"];
            for (const field of possibleTypeFields) {
                packagingFields.push(field);
            }
            
            const packagingResults = await this.pos.data.searchRead(
                "product.packaging",
                [["barcode", "ilike", searchProductWord]],
                packagingFields,
                {}
            );
            
            console.log("Packaging search results:", packagingResults);
            
            if (packagingResults && packagingResults.length > 0) {
                // Create a map of product_id -> packaging for tracking
                const productPackagingMap = new Map();
                packagingResults.forEach(pkg => {
                    if (pkg.product_id && pkg.product_id.length > 0) {
                        const productId = pkg.product_id[0];
                        if (!productPackagingMap.has(productId)) {
                            productPackagingMap.set(productId, pkg);
                        }
                    }
                });
                
                // Get unique product IDs from packagings
                const productIds = [...productPackagingMap.keys()];
                
                if (productIds.length > 0) {
                    // Load these products if they're not already loaded
                    const domain = [
                        ["id", "in", productIds],
                        ["available_in_pos", "=", true],
                        ["sale_ok", "=", true],
                    ];
                    
                    const { limit_categories, iface_available_categ_ids } = this.pos.config;
                    if (limit_categories && iface_available_categ_ids.length > 0) {
                        domain.push(["pos_categ_ids", "in", iface_available_categ_ids]);
                    }
                    
                    const packagingProducts = await this.pos.data.searchRead(
                        "product.product",
                        domain,
                        this.pos.data.fields["product.product"],
                        {
                            context: { display_default_code: false },
                            offset: 0,
                            limit: 30,
                        }
                    );
                    
                    if (packagingProducts && packagingProducts.length > 0) {
                        // Process and add these products
                        await this.pos.data.processData(packagingProducts, "product.product");
                        await this.pos.processProductAttributes();
                        
                        // Store packaging matches for loaded products
                        packagingProducts.forEach(product => {
                            const packaging = productPackagingMap.get(product.id);
                            if (packaging) {
                                // Get the packaging object from the model
                                const packagingModel = this.pos.models["product.packaging"];
                                if (packagingModel) {
                                    const packagingObj = packagingModel.get(packaging.id);
                                    if (packagingObj) {
                                        // Store both the model object and raw data for package_type_id access
                                        this.packagingMatches.set(product.id, {
                                            model: packagingObj,
                                            raw: packaging  // Keep raw data for package_type_id access
                                        });
                                    }
                                }
                            }
                        });
                    }
                }
            }
        } catch (error) {
            console.error("Error searching packaging barcodes:", error);
        }
        
        return standardResults;
    },

    /**
     * Override getProductsBySearchWord to also search in packaging barcodes
     * for products already loaded in the POS
     */
    getProductsBySearchWord(searchWord) {
        const words = unaccent(searchWord.toLowerCase(), false);
        const products = this.pos.selectedCategory?.id
            ? this.getProductsByCategory(this.pos.selectedCategory)
            : this.products;

        // First, filter by standard searchString (includes name, barcode, default_code)
        let filteredProducts = products.filter((p) => unaccent(p.searchString).includes(words));
        
        // Also search in packaging barcodes for products already loaded
        const packagingModel = this.pos.models["product.packaging"];
        if (packagingModel && words.length > 0) {
            try {
                // Get all packagings - try both getAllBy and getAll methods
                let packagingByBarcode = {};
                
                try {
                    packagingByBarcode = packagingModel.getAllBy("barcode") || {};
                } catch (e) {
                    // If getAllBy doesn't work, try getting all and filtering
                    const allPackagings = packagingModel.getAll() || [];
                    allPackagings.forEach(pkg => {
                        if (pkg && pkg.barcode) {
                            packagingByBarcode[pkg.barcode] = pkg;
                        }
                    });
                }
                
                // Find packagings with matching barcodes
                for (const [barcode, packaging] of Object.entries(packagingByBarcode)) {
                    if (packaging && packaging.barcode) {
                        const barcodeLower = unaccent(packaging.barcode.toLowerCase());
                        if (barcodeLower.includes(words)) {
                            // Get the product from packaging
                            // packaging.product_id should be a Many2one field that returns the product directly
                            const product = packaging.product_id;
                            if (product) {
                                // Check if this product is in our products list
                                const productInList = products.find(p => p.id === product.id);
                                if (productInList && !filteredProducts.includes(productInList)) {
                                    filteredProducts.push(productInList);
                                    // Store packaging match for this product
                                    this.packagingMatches.set(product.id, packaging);
                                }
                            }
                        }
                    }
                }
            } catch (error) {
                console.error("Error in packaging barcode search:", error);
            }
        }

        return filteredProducts.sort((a, b) => {
            const nameA = unaccent(a.searchString);
            const nameB = unaccent(b.searchString);
            // Sort by match index, push non-matching items to the end, and use alphabetical order as a tiebreaker
            return nameA.indexOf(words) - nameB.indexOf(words) || nameA.localeCompare(nameB);
        });
    },

    /**
     * Override addProductToOrder to handle packaging when product was found via packaging barcode
     */
    async addProductToOrder(product) {
        if (this.searchWord && product.isConfigurable()) {
            const barcode = this.searchWord;
            const searchedProduct = product.variants.filter(
                (p) => p.barcode && p.barcode.includes(barcode)
            );
            if (searchedProduct.length === 1) {
                product = searchedProduct[0];
            }
        }
        
        // Check if this product was found via packaging barcode
        // Only use packaging info if we have an active search word AND it matches a packaging barcode
        const searchWord = this.searchWord || this.pos.searchProductWord;
        const hasActiveSearch = searchWord && searchWord.trim().length > 0;
        
        // Check if the search word matches a packaging barcode
        let packagingMatch = null;
        if (hasActiveSearch && this.packagingMatches.has(product.id)) {
            // Verify the search word actually matches a packaging barcode
            const packagingModel = this.pos.models["product.packaging"];
            if (packagingModel) {
                const searchTerm = searchWord.trim().toLowerCase();
                const match = this.packagingMatches.get(product.id);
                const packaging = match.model || match;
                const packagingRaw = match.raw || match;
                const packagingBarcode = (packagingRaw?.barcode || packaging?.barcode || "").toLowerCase();
                
                // Only use packaging if search word matches the packaging barcode
                if (packagingBarcode.includes(searchTerm) || searchTerm.includes(packagingBarcode)) {
                    packagingMatch = match;
                }
            }
        }
        
        if (packagingMatch) {
            // Extract packaging object (could be direct object or {model, raw} structure)
            const packaging = packagingMatch.model || packagingMatch;
            const packagingRaw = packagingMatch.raw || packagingMatch;
            
            console.log("Adding product with packaging. Raw:", packagingRaw);
            console.log("Packaging qty:", packagingRaw.qty);
            
            // Set quantity in the initial values, not just in options
            const initialQty = packagingRaw.qty || packaging.qty || 1;
            
            // Add product with packaging info
            await reactive(this.pos).addLineToCurrentOrder(
                { product_id: product, qty: initialQty },
                { packaging: packaging, packagingRaw: packagingRaw }
            );
            // Clear the match after adding
            this.packagingMatches.delete(product.id);
        } else {
            // Normal product addition - ensure no packaging info is passed
            // Also clear any stale packaging matches for this product
            if (this.packagingMatches.has(product.id)) {
                this.packagingMatches.delete(product.id);
            }
            await reactive(this.pos).addLineToCurrentOrder({ product_id: product }, {});
        }
    },
});

