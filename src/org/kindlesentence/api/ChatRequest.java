package org.kindlesentence.api;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.json.simple.JSONValue;
import org.json.simple.parser.JSONParser;
import org.kindlesentence.core.ExplanationFailure;
import org.kindlesentence.core.ExplanationRequest;

public final class ChatRequest implements ExplanationRequest {
    private final String selection;
    private Process process;
    private boolean cancelled;

    public ChatRequest(String selection) {
        this.selection = selection;
    }

    public static String encode(ApiConfig config, String selection) {
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("model", config.model);
        request.put("messages", Arrays.asList(
                message("system", config.instruction),
                message("user", selection)));
        if (config.provider == ApiConfig.Provider.OPENAI) {
            request.put("max_completion_tokens", 1024);
            request.put("store", false);
        } else {
            request.put("max_tokens", 1024);
            if (config.provider == ApiConfig.Provider.EVREN) {
                request.put("reasoning_effort", "low");
            } else {
                Map<String, String> thinking = new LinkedHashMap<>();
                thinking.put("type", "disabled");
                request.put("thinking", thinking);
            }
        }
        request.put("stream", false);
        return JSONValue.toJSONString(request);
    }

    private static Map<String, Object> message(String role, String content) {
        Map<String, Object> message = new LinkedHashMap<>();
        message.put("role", role);
        message.put("content", content);
        return message;
    }

    public static String decode(String body, int status) throws ExplanationFailure {
        if (status == 401 || status == 403) throw new ExplanationFailure("API access denied. Check your key and account.");
        if (status == 402 || status == 429) throw new ExplanationFailure("API limit reached. Try again later.");
        if (status != 200) throw new ExplanationFailure("Service unavailable. Try again later.");
        try {
            Map<?, ?> response = (Map<?, ?>) new JSONParser().parse(body);
            Map<?, ?> choice = (Map<?, ?>) ((List<?>) response.get("choices")).get(0);
            if (!"stop".equals(choice.get("finish_reason"))) {
                throw new ExplanationFailure("Explanation incomplete. Try a shorter selection.");
            }
            Map<?, ?> message = (Map<?, ?>) choice.get("message");
            Object value = message.get("content");
            if (!(value instanceof String) || ((String) value).trim().isEmpty()) {
                throw new ExplanationFailure("No explanation returned. Try again later.");
            }
            return ((String) value).trim();
        } catch (ExplanationFailure failure) {
            throw failure;
        } catch (Exception failure) {
            throw new ExplanationFailure("Unexpected service response. Try again later.");
        }
    }

    @Override
    public String execute() throws Exception {
        ApiConfig config = ApiConfig.load();
        String header = config.provider.headerPath();
        if (!new File(header).canRead()) throw new ExplanationFailure("API key unavailable. Check setup.");
        Process running = new ProcessBuilder("/usr/bin/curl", "--silent", "--show-error",
                "--connect-timeout", "10", "--max-time", "45", "--max-filesize", "65536",
                "--proto", "=https", "-H", "@" + header,
                "-H", "Content-Type: application/json", "--data-binary", "@-",
                "--write-out", "\n%{http_code}",
                config.provider.endpoint)
                .redirectError(new File("/dev/null")).start();
        synchronized (this) {
            if (cancelled) {
                running.destroy();
                throw new InterruptedException();
            }
            process = running;
        }
        try {
            try (OutputStream input = running.getOutputStream()) {
                input.write(encode(config, selection).getBytes(StandardCharsets.UTF_8));
            }
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            try (InputStream output = running.getInputStream()) {
                byte[] buffer = new byte[2048];
                int count;
                while ((count = output.read(buffer)) != -1) {
                    if (bytes.size() + count > 65536) throw new ExplanationFailure("Service response too large.");
                    bytes.write(buffer, 0, count);
                }
            }
            int exit = running.waitFor();
            if (exit == 28) throw new ExplanationFailure("Request timed out. Close and try again.");
            if (exit == 6 || exit == 7) throw new ExplanationFailure("Cannot connect. Check Wi-Fi.");
            if (exit != 0) throw new ExplanationFailure("Secure connection failed. Check Wi-Fi or try later.");
            String response = new String(bytes.toByteArray(), StandardCharsets.UTF_8);
            int split = response.lastIndexOf('\n');
            if (split < 0) throw new ExplanationFailure("Unexpected service response.");
            return decode(response.substring(0, split), Integer.parseInt(response.substring(split + 1).trim()));
        } finally {
            running.destroy();
            synchronized (this) { process = null; }
        }
    }

    @Override
    public synchronized void cancel() {
        cancelled = true;
        if (process != null) process.destroy();
    }
}
