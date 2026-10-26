package org.kindlesentence.install;

import java.io.*;
import java.util.Properties;
import org.kindlesentence.api.ApiConfig;

public final class ImportSettings {
    private static String step = "input";
    public static void main(String[] args) {
        try {
            if (args.length != 2) throw new IOException();
            prepare(new File(args[0]), new File(args[1]));
        } catch (Throwable failure) {
            System.err.println("SETTINGS_FAILURE " + step + " " + failure.getClass().getName());
            System.exit(1);
        }
    }

    static void prepare(File input, File stage) throws Exception {
        if (!input.isFile() || input.length() > 32768 || !stage.isDirectory()) throw new IOException();
        Properties values = new Properties();
        try (InputStream in = new FileInputStream(input)) { values.load(in); }
        step = "fields";
        for (Object key : values.keySet()) {
            if (!"provider".equals(key) && !"model".equals(key)
                    && !"api_key".equals(key) && !"instruction".equals(key)) throw new IOException();
        }
        step = "config";
        ApiConfig config = ApiConfig.parse(values);
        step = "key-format";
        String key = values.getProperty("api_key", "");
        if (key.length() > 4096 || (!key.isEmpty() && !key.matches("[!-~]+"))) throw new IOException();
        step = "write-config";
        Properties settings = new Properties();
        settings.setProperty("provider", config.provider.id);
        settings.setProperty("model", config.model);
        settings.setProperty("instruction", config.instruction);
        try (OutputStream out = new FileOutputStream(new File(stage, "api.properties"))) {
            settings.store(out, "Sentence Assistant");
        }
        step = "write-header";
        if (!key.isEmpty()) {
            String prefix = config.provider == ApiConfig.Provider.EVREN ? "X-API-Key: " : "Authorization: Bearer ";
            write(new File(stage, "header"), prefix + key + "\n");
        }
        step = "write-provider";
        write(new File(stage, "provider"), config.provider.id);
    }

    private static void write(File file, String value) throws IOException {
        try (OutputStream out = new FileOutputStream(file)) { out.write(value.getBytes("US-ASCII")); }
    }
}
