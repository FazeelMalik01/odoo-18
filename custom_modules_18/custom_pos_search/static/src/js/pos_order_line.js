/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

patch(PosOrderline.prototype, {
    setup(vals) {
        super.setup(vals);
        // Store packaging info if passed in vals
        if (vals._packagingInfo) {
            this._packagingInfo = vals._packagingInfo;
        }
    },

    setOptions(options) {
        super.setOptions(options);
        
        // Handle packaging from search
        if (options.packaging) {
            const packaging = options.packaging;
            console.log("Packaging object:", packaging);
            console.log("Packaging raw:", options.packagingRaw);
            console.log("Current qty before:", this.qty);
            
            // Set quantity to packaging contained quantity
            // Try from raw data first (most reliable), then from model object
            let packagingQty = null;
            if (options.packagingRaw && typeof options.packagingRaw.qty !== 'undefined') {
                packagingQty = options.packagingRaw.qty;
                console.log("Got qty from packagingRaw:", packagingQty);
            } else if (packaging.qty) {
                packagingQty = packaging.qty;
                console.log("Got qty from packaging:", packagingQty);
            } else if (packaging.raw && packaging.raw.qty) {
                packagingQty = packaging.raw.qty;
                console.log("Got qty from packaging.raw:", packagingQty);
            }
            
            if (packagingQty !== null && packagingQty !== undefined) {
                console.log("Setting quantity to:", packagingQty, "Type:", typeof packagingQty);
                this.set_quantity(Number(packagingQty));
                console.log("Qty after set_quantity:", this.qty);
            } else {
                console.log("No quantity found. packagingRaw:", options.packagingRaw, "packaging:", packaging);
            }
            
            // Modify product name to include package type
            this._updateProductNameWithPackaging(packaging, options);
        }
    },

    /**
     * Update product name to include packaging type
     */
    _updateProductNameWithPackaging(packaging, options) {
        // Get package type - prioritize package_type_id.name over packaging name
        let packageType = "";
        
        console.log("Updating product name with packaging:", packaging);
        console.log("Options:", options);
        console.log("Packaging raw from options:", options?.packagingRaw);
        
        // Try to get package_type_id - handle different formats
        // First try from raw data (most reliable for Many2one fields)
        let packageTypeId = null;
        let packageTypeName = null;
        
        if (options?.packagingRaw) {
            packageTypeId = options.packagingRaw.package_type_id || options.packagingRaw.packaging_type_id;
        }
        
        // If not found, try from packaging object
        if (!packageTypeId) {
            packageTypeId = packaging.package_type_id || packaging.packaging_type_id;
        }
        
        // Also try from packaging.raw if available
        if (!packageTypeId && packaging.raw) {
            packageTypeId = packaging.raw.package_type_id || packaging.raw.packaging_type_id;
        }
        
        console.log("Package type ID:", packageTypeId);
        
        if (packageTypeId) {
            // Handle Many2one field formats:
            // 1. Array format [id, name] from searchRead (most common)
            if (Array.isArray(packageTypeId) && packageTypeId.length > 1) {
                packageType = packageTypeId[1];
                console.log("Found package type from array:", packageType);
            }
            // 2. If it's just an ID (number), try to get from stock.package.type model
            else if (typeof packageTypeId === 'number') {
                console.log("Package type ID is a number:", packageTypeId);
                const packageTypeModel = this.models["stock.package.type"];
                console.log("Package type model:", packageTypeModel);
                if (packageTypeModel) {
                    const packageTypeObj = packageTypeModel.get(packageTypeId);
                    console.log("Package type object from model:", packageTypeObj);
                    if (packageTypeObj && packageTypeObj.name) {
                        packageType = packageTypeObj.name;
                        console.log("Found package type from model:", packageType);
                    } else {
                        console.log("Package type object not found or has no name");
                        // Try to load it from the server if not in model
                        this._loadPackageTypeNameAsync(packageTypeId);
                    }
                } else {
                    console.log("stock.package.type model not available, trying to load from server");
                    // Try to load it from the server
                    this._loadPackageTypeNameAsync(packageTypeId);
                }
            }
            // 3. Object format with .name property
            else if (packageTypeId.name) {
                packageType = packageTypeId.name;
                console.log("Found package type from object.name:", packageType);
            }
            // 4. Try raw data if available
            else if (packageTypeId.raw && packageTypeId.raw.name) {
                packageType = packageTypeId.raw.name;
                console.log("Found package type from raw.name:", packageType);
            }
            // 5. If it's a model object, try to get name directly
            else if (typeof packageTypeId === 'object' && 'name' in packageTypeId) {
                packageType = packageTypeId.name;
                console.log("Found package type from object:", packageType);
            }
        }
        
        console.log("Final package type:", packageType);
        
        // If we still don't have package type, don't show anything (don't fall back to packaging name)
        if (packageType) {
            // Get the base product name (before we modify it)
            const baseName = this.product_id.display_name;
            // Add package type above the product name
            this.full_product_name = `[${packageType}] ${baseName}`;
            console.log("Updated product name to:", this.full_product_name);
        } else {
            console.log("No package type found, product name unchanged");
        }
    },

    /**
     * Load package type name from server asynchronously
     */
    async _loadPackageTypeNameAsync(packageTypeId) {
        try {
            console.log("Loading package type name for ID:", packageTypeId);
            // Access POS data service through order
            const pos = this.order_id?.pos;
            if (pos && pos.data) {
                const result = await pos.data.searchRead(
                    "stock.package.type",
                    [["id", "=", packageTypeId]],
                    ["name"],
                    { limit: 1 }
                );
                console.log("Package type search result:", result);
                if (result && result.length > 0 && result[0].name) {
                    const packageType = result[0].name;
                    const baseName = this.product_id.display_name;
                    this.full_product_name = `[${packageType}] ${baseName}`;
                    console.log("Updated product name with package type:", this.full_product_name);
                }
            } else {
                console.log("POS data service not available");
            }
        } catch (error) {
            console.error("Error loading package type:", error);
        }
    },
});

