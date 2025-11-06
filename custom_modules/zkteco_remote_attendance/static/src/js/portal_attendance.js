/** @odoo-module **/
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

class PortalAttendance {
    constructor() {
        this.libraryLoaded = false;
        this.start();
    }

    async start() {
        await this.loadPlusCodeLibrary();
        // this.captureLocation();
        // this.setupLogoutListener();
        // Check if user is on /my (portal home)
        // if (window.location.pathname.startsWith("/my")) {
        //     this.captureLocation();
        //     this.setupLogoutListener();
        // } else {
        //     console.log("📍 Not on /my page. Skipping location capture.");
        // }
        if (window.location.pathname.startsWith("/my")) {
            // Check if we've already tried to mark attendance in this session
            const alreadyAttempted = localStorage.getItem("attendanceAttempted");
            this.setupLogoutListener();
            if (!alreadyAttempted) {
                console.log("📍 Attempting to capture location and mark attendance...");
                this.captureLocation();
                
            } else {
                console.log("✅ Attendance already attempted. Skipping...");
            }
        }

    }

    async loadPlusCodeLibrary() {
        if (window.openlocationcode) {
            console.log(" OpenLocationCode already loaded.");
            this.libraryLoaded = true;
            return;
        }

        return new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = "https://cdnjs.cloudflare.com/ajax/libs/openlocationcode/1.0.3/openlocationcode.min.js"; // Correct URL
            script.onload = () => {
                if (window.OpenLocationCode) {
                    this.libraryLoaded = true;
                    resolve();
                } else {
                    console.error("🚨 OpenLocationCode is undefined after loading.");
                    reject();
                }
            };
            script.onerror = () => {
                console.error("🚨 Failed to load Plus Code library.");
                reject();
            };
            document.head.appendChild(script);
        });
    }


    async captureLocation() {
        if (!navigator.geolocation) {
            console.error("🚨 Geolocation is not supported by this browser.");
            return;
        }

        navigator.geolocation.getCurrentPosition(
            async (position) => {
                // console.log("High Accuracy:", position),
                //   console.log(`✅ GPS Coordinates: Latitude: ${position.coords.latitude}, Longitude: ${position.coords.longitude}`);
                await this._onSuccess(position);
            },
            (error) => this._onError(error),
            {
                enableHighAccuracy: true, // Ensure high accuracy
                timeout: 15000, // Wait up to 10 seconds
                maximumAge: 0, // Do not use cached location
            }
        );
        // navigator.permissions.query({ name: 'geolocation' }).then(console.log);
    }

    async _onSuccess(position) {
        
        localStorage.setItem("attendanceAttempted", "1");
        if (!this.libraryLoaded) {
            console.warn("⏳ Waiting for Plus Code library to load...");
            await this.loadPlusCodeLibrary();
        }

        const lat = position.coords.latitude;
        const long = position.coords.longitude;

        //console.log(`✅ Using Coordinates: Latitude: ${lat}, Longitude: ${long}`);

        // Generate Full Plus Code (GLOBAL)
        const plusCode = OpenLocationCode.encode(lat, long);
        //console.log(`📍 Generated Full Plus Code: ${plusCode}`);
        alert(`Your location code: ${plusCode} Please verify your location code on google maps.`);

        // Send coordinates to check if within range
        this.checkLocationWithinRange(lat, long);
    }

    async checkLocationWithinRange(lat, long) {
        try {
            const response = await rpc("/remote_attendance/check", {
                lat: lat,
                long: long,
            });

            if (response.success) {
                alert("✅ Attendance marked successfully.");
            } else {
                alert("❌ Attendance not marked: ", response.message);
            }
        } catch (error) {
            console.error("🚨 Error checking location range:", error);
        }
    }


    _onError(error) {
        //console.error("🚨 Geolocation error: ", error.message);
        localStorage.setItem("attendanceAttempted", "1");
    }

    async sendLocationToBackend(plus_code) {
        try {
            const response = await rpc("/remote_attendance/check", {
                plus_code: plus_code,
            });

            if (response.success) {
                alert("✅ Attendance marked successfully.");
            } else {
                alert("❌ Attendance not marked: ", response.message);
            }
        } catch (error) {
            console.error("🚨 Error sending location to backend:", error);
        }
    }

    async sendCheckoutToBackend() {
        try {
            const response = await rpc("/remote_attendance/checkout", {});

            if (response.success) {
                alert("✅ Checkout marked successfully.");
            } else {
                alert("❌ Checkout not marked: ", response.message);
            }
        } catch (error) {
            console.error("🚨 Error sending checkout to backend:", error);
        }
    }

    setupLogoutListener() {
        const logoutButton = document.querySelector('a[href*="/web/session/logout"]');
        if (logoutButton) {
            logoutButton.addEventListener("click", async (event) => {
                //console.log("🚪 User logging out...");
                await this.sendCheckoutToBackend();
                localStorage.removeItem("attendanceAttempted");
            });
        }
    }

}

// ✅ Register as a service
registry.category("services").add("PortalAttendance", {
    start(env) {
        return new PortalAttendance();
    },
});


