/** @odoo-module **/

/**
 * RTL/LTR Utility Functions for Mixed Language Support
 * Handles Arabic/English text direction in POS
 */

// Arabic Unicode range: \u0600-\u06FF (Arabic), \u0750-\u077F (Arabic Supplement), 
// \u08A0-\u08FF (Arabic Extended-A), \uFB50-\uFDFF (Arabic Presentation Forms-A),
// \uFE70-\uFEFF (Arabic Presentation Forms-B)
const ARABIC_REGEX = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/;

/**
 * Check if a string contains Arabic characters
 * @param {string} text - Text to check
 * @returns {boolean} - True if contains Arabic
 */
export function containsArabic(text) {
    if (!text || typeof text !== 'string') return false;
    return ARABIC_REGEX.test(text);
}

/**
 * Determine text direction based on content
 * @param {string} text - Text to analyze
 * @returns {string} - 'rtl' for Arabic, 'ltr' for others
 */
export function getTextDirection(text) {
    return containsArabic(text) ? 'rtl' : 'ltr';
}

/**
 * Parse attribute string like "(Color: Red, Size: Large, النوع: دجاج)"
 * into individual attribute-value pairs
 * @param {string} attributeString - String containing attributes in parentheses
 * @returns {Array<{text: string, dir: string}>} - Array of attribute objects with text and direction
 */
export function parseAttributeString(attributeString) {
    if (!attributeString || typeof attributeString !== 'string') return [];
    
    // Remove surrounding parentheses if present
    let cleaned = attributeString.trim();
    if (cleaned.startsWith('(') && cleaned.endsWith(')')) {
        cleaned = cleaned.slice(1, -1);
    }
    
    if (!cleaned) return [];
    
    // Split by comma (considering spaces)
    const parts = cleaned.split(/\s*,\s*/);
    
    return parts.map(part => ({
        text: part.trim(),
        dir: getTextDirection(part)
    })).filter(item => item.text);
}

/**
 * Parse full product name with variants
 * @param {string} fullName - Full product name like "Product Name (attr1, attr2)"
 * @returns {{productName: string, productNameDir: string, attributes: Array}} - Parsed product info
 */
export function parseFullProductName(fullName) {
    if (!fullName || typeof fullName !== 'string') {
        return {
            productName: '',
            productNameDir: 'ltr',
            attributes: []
        };
    }
    
    const openParenIndex = fullName.indexOf('(');
    
    if (openParenIndex >= 0) {
        const productName = fullName.substring(0, openParenIndex).trim();
        const attributeString = fullName.substring(openParenIndex).trim();
        
        return {
            productName: productName,
            productNameDir: getTextDirection(productName),
            attributes: parseAttributeString(attributeString)
        };
    }
    
    return {
        productName: fullName,
        productNameDir: getTextDirection(fullName),
        attributes: []
    };
}

/**
 * Create BDI (Bidirectional Isolation) HTML element string for a text
 * @param {string} text - Text content
 * @param {string} [dir] - Direction override (auto-detected if not provided)
 * @returns {string} - HTML string with bdi element
 */
export function createBdiElement(text, dir = null) {
    const direction = dir || getTextDirection(text);
    return `<bdi dir="${direction}">${escapeHtml(text)}</bdi>`;
}

/**
 * Escape HTML special characters
 * @param {string} text - Text to escape
 * @returns {string} - Escaped text
 */
export function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format attributes array with proper RTL/LTR for display
 * @param {Array<{text: string, dir: string}>} attributes - Array of attribute objects
 * @param {string} separator - Separator between attributes
 * @returns {string} - HTML string with properly directed attributes
 */
export function formatAttributesHtml(attributes, separator = ', ') {
    if (!attributes || !attributes.length) return '';
    
    const htmlParts = attributes.map(attr => createBdiElement(attr.text, attr.dir));
    return '(' + htmlParts.join(separator) + ')';
}

console.log("✅ RTL/LTR utilities loaded for mixed language support");

