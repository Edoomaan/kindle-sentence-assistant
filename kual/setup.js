"use strict";
const defaults = {evren: "qwen3.8-flash-next", openai: "", deepseek: ""};
function propertiesValue(value) {
    return Array.from(value).map(char => {
        if (char === "\\") return "\\\\";
        if (char === "\n") return "\\n";
        if (char === "\r") return "\\r";
        if (char === "\t") return "\\t";
        if (" =:#!".includes(char)) return "\\" + char;
        if (char.charCodeAt(0) > 126) {
            return char.split("").map(unit => "\\u" + unit.charCodeAt(0).toString(16).padStart(4, "0")).join("");
        }
        return char;
    }).join("");
}
function encodeSettings(provider, model, key, instruction) {
    if (!Object.hasOwn(defaults, provider)) throw new Error("Choose a provider.");
    if (!/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/.test(model)) throw new Error("Enter a valid model ID from your provider.");
    if (key.length > 4096 || (key && !/^[!-~]+$/.test(key))) throw new Error("The API key must not contain spaces or line breaks.");
    if (!instruction.trim()) throw new Error("Enter explanation preferences, including your preferred language.");
    if (instruction.length > 2000 || /[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/.test(instruction)) throw new Error("Preferences must be at most 2000 characters, without control characters.");
    return Object.entries({provider, model, api_key: key, instruction}).map(([name, value]) => name + "=" + propertiesValue(value)).join("\n") + "\n";
}
if (typeof module !== "undefined") module.exports = {encodeSettings};
if (typeof document !== "undefined") {
    const form = document.querySelector("form");
    const provider = document.querySelector("#provider");
    const model = document.querySelector("#model");
    provider.addEventListener("change", () => { model.value = defaults[provider.value]; });
    form.addEventListener("submit", event => {
        event.preventDefault();
        const status = document.querySelector("#status");
        const key = document.querySelector("#key");
        try {
            const text = encodeSettings(provider.value, model.value.trim(), key.value, document.querySelector("#instruction").value);
            const url = URL.createObjectURL(new Blob([text], {type: "text/plain;charset=us-ascii"}));
            const link = document.createElement("a");
            link.href = url;
            link.download = "setup.properties";
            link.click();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
            key.value = "";
            status.textContent = "Copy setup.properties into the Kindle installer folder, then choose Import settings in KUAL. After import, delete this downloaded copy from your computer.";
        } catch (error) { status.textContent = error.message; }
    });
}
