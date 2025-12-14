console.log("Loader: File loaded! (Version 4.0.0)");

class PasswordDashboardLoader extends HTMLElement {
  set hass(hass) {
    if (!this.isLoaded) {
      this.isLoaded = true;
      this.loadDashboard(hass);
    }
  }

  // Helper to load external scripts/styles only once
  async loadExternalResource(type, url) {
    return new Promise((resolve, reject) => {
      // Check if it already exists
      if (
        document.querySelector(`${type}[src="${url}"], link[href="${url}"]`)
      ) {
        resolve();
        return;
      }

      let element;
      if (type === "script") {
        element = document.createElement("script");
        element.src = url;
        element.onload = resolve;
        element.onerror = reject;
      } else {
        element = document.createElement("link");
        element.rel = "stylesheet";
        element.href = url;
        element.onload = resolve;
        element.onerror = reject;
      }
      document.head.appendChild(element);
    });
  }

  async loadDashboard(hass) {
    this.innerHTML = `
      <div style="padding: 40px; text-align: center;">
        <h2>Loading Dashboard...</h2>
        <p>Fetching secure view...</p>
      </div>
    `;

    try {
      await Promise.all([
        this.loadExternalResource("link", "/local/tis_assets/dashboard.css"),
        this.loadExternalResource(
          "link",
          "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"
        ),
      ]);

      const response = await hass.fetchWithAuth("/api/password-dashboard");
      if (response.status !== 200) {
        this.innerHTML = `<h3>Error: ${response.status} - ${response.statusText}</h3>`;
        return;
      }
      const htmlText = await response.text();

      this.innerHTML = "";
      window.HASS_AUTH_TOKEN = hass.auth.data.access_token;

      // 3. Parse & Inject HTML
      const parser = new DOMParser();
      const doc = parser.parseFromString(htmlText, "text/html");

      const styles = doc.querySelectorAll("style");
      styles.forEach((style) => this.appendChild(style));

      const range = doc.createRange();
      range.selectNode(this); // Set context to this element
      const fragment = range.createContextualFragment(htmlText);
      this.appendChild(fragment);

      // 4. Extract & Execute Scripts
      const scripts = doc.querySelectorAll("script");
      scripts.forEach((oldScript) => {
        const newScript = document.createElement("script");
        if (oldScript.src) {
          newScript.src = oldScript.src;
        } else {
          newScript.textContent = oldScript.textContent;
        }
        this.appendChild(newScript);
      });

      // 6. Handoff
      setTimeout(() => {
        const dashboardRoot = this.querySelector("#pw-dashboard-root");
        if (window.initPasswordDashboard && dashboardRoot) {
          window.initPasswordDashboard(dashboardRoot);
        } else {
          console.error("Loader: Script not ready or root not found.");
        }
      }, 200);
    } catch (err) {
      console.error("Loader Exception:", err);
      this.innerHTML = `<pre style="color:red; padding:20px;">Error:\n${err.stack}</pre>`;
    }
  }
}

customElements.define("password-dashboard-loader", PasswordDashboardLoader);
