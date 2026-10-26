package org.kindlesentence.api;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.util.Properties;
import org.kindlesentence.core.ExplanationFailure;

public final class ApiConfig {
    public static final String DIRECTORY = "/var/local/sentence-assistant";

    public enum Provider {
        EVREN("evren", "https://evren-llmapi.ssyz.org.tr/v1/chat/completions"),
        OPENAI("openai", "https://api.openai.com/v1/chat/completions"),
        DEEPSEEK("deepseek", "https://api.deepseek.com/chat/completions");

        public final String id;
        public final String endpoint;

        Provider(String id, String endpoint) {
            this.id = id;
            this.endpoint = endpoint;
        }

        public String headerPath() {
            return DIRECTORY + "/" + id + "-header";
        }
    }

    public final Provider provider;
    public final String model;
    public final String instruction;

    private ApiConfig(Provider provider, String model, String instruction) {
        this.provider = provider;
        this.model = model;
        this.instruction = instruction;
    }

    public static ApiConfig parse(Properties values) throws ExplanationFailure {
        String name = values.getProperty("provider", "");
        String model = values.getProperty("model", "");
        if (!model.matches("[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")) {
            throw new ExplanationFailure("Invalid API model. Check setup.");
        }
        String instruction = values.getProperty("instruction", "").trim();
        if (instruction.isEmpty()) throw new ExplanationFailure("Set explanation preferences in setup.html and import settings.");
        if (instruction.length() > 2000 || instruction.matches("(?s).*[\\x00-\\x08\\x0B\\x0C\\x0E-\\x1F\\x7F].*")) {
            throw new ExplanationFailure("Invalid explanation preferences. Check setup.");
        }
        for (Provider provider : Provider.values()) {
            if (provider.id.equals(name)) return new ApiConfig(provider, model, instruction);
        }
        throw new ExplanationFailure("Unknown API provider. Check setup.");
    }

    public static ApiConfig load() throws ExplanationFailure {
        File file = new File(DIRECTORY, "api.properties");
        if (!file.exists()) throw new ExplanationFailure("Import API settings from setup.html first.");
        try (InputStream input = new FileInputStream(file)) {
            if (file.length() > 16384) throw new ExplanationFailure("Invalid API settings. Check setup.");
            Properties values = new Properties();
            values.load(input);
            return parse(values);
        } catch (ExplanationFailure failure) {
            throw failure;
        } catch (Exception failure) {
            throw new ExplanationFailure("Cannot read API settings. Check setup.");
        }
    }
}
