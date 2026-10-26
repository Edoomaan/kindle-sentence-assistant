package org.kindlesentence.nativeui;

import java.util.List;
import java.util.Map;
import java.util.Properties;
import org.kindlesentence.api.ApiConfig;
import org.json.simple.parser.JSONParser;
import org.kindlesentence.api.ChatRequest;
import org.kindlesentence.core.ExplanationFailure;

public final class ChatRequestTest {
    public static void main(String[] args) throws Exception {
        String selected = "  He said \"don’t\".\n\\ $() `cmd` 😀\t";
        Map<?, ?> request = (Map<?, ?>) new JSONParser().parse(ChatRequest.encode(config("evren", "qwen3.8-flash-next"), selected));
        List<?> messages = (List<?>) request.get("messages");
        require(messages.size() == 2, "only configured instruction and selected text");
        require(selected.equals(((Map<?, ?>) messages.get(1)).get("content")), "JSON roundtrip preserves selection");
        require("qwen3.8-flash-next".equals(request.get("model")), "selected model");
        String answer = "{\"choices\":[{\"finish_reason\":\"stop\",\"message\":{\"content\":\"  Simple answer.  \",\"reasoning\":\"not for display\"}}]}";
        require("Simple answer.".equals(ChatRequest.decode(answer, 200)), "only content is displayed");
        rejected(answer.replace("stop", "length"), 200);
        rejected("{}", 200);
        rejected("not JSON", 200);
        rejected(answer, 401);
        rejected(answer, 403);
        rejected(answer, 429);
        rejected(answer, 503);
        rejected(answer.replace("  Simple answer.  ", ""), 200);
        for (String provider : new String[] {"evren", "openai", "deepseek"}) {
            ApiConfig config = config(provider, "test-model");
            Map<?, ?> payload = (Map<?, ?>) new JSONParser().parse(ChatRequest.encode(config, selected));
            require(config.provider.headerPath().endsWith("/" + provider + "-header"), "provider keys are separate");
            require("test-model".equals(payload.get("model")), "configured model is used");
            if (provider.equals("openai")) {
                require(payload.containsKey("max_completion_tokens") && !payload.containsKey("max_tokens"), "OpenAI token field");
                require(Boolean.FALSE.equals(payload.get("store")), "OpenAI stored completions disabled");
                require(!payload.containsKey("reasoning_effort"), "no unsupported reasoning option forced on OpenAI");
                require("https://api.openai.com/v1/chat/completions".equals(config.provider.endpoint), "OpenAI endpoint");
            } else if (provider.equals("deepseek")) {
                require("disabled".equals(((Map<?, ?>) payload.get("thinking")).get("type")), "DeepSeek non-thinking mode");
                require(!payload.containsKey("reasoning_effort"), "no conflicting thinking options");
                require("https://api.deepseek.com/chat/completions".equals(config.provider.endpoint), "DeepSeek endpoint");
            } else {
                require("low".equals(payload.get("reasoning_effort")), "Evren behavior retained");
            }
        }
        Properties preferences = new Properties();
        preferences.setProperty("provider", "evren");
        preferences.setProperty("model", "test-model");
        preferences.setProperty("instruction", "Anlamı Türkçe açıkla.\nExplain metaphors briefly.");
        Map<?, ?> custom = (Map<?, ?>) new JSONParser().parse(ChatRequest.encode(ApiConfig.parse(preferences), selected));
        String system = (String) ((Map<?, ?>) ((List<?>) custom.get("messages")).get(0)).get("content");
        require(system.equals(preferences.getProperty("instruction")), "exact custom instruction without hidden rules");
        preferences.setProperty("instruction", "   ");
        try { ApiConfig.parse(preferences); throw new AssertionError("Blank preference accepted"); }
        catch (ExplanationFailure expected) { }
        preferences.setProperty("instruction", new String(new char[2001]).replace('\0', 'x'));
        try { ApiConfig.parse(preferences); throw new AssertionError("Oversized preference accepted"); }
        catch (ExplanationFailure expected) { }
        preferences.setProperty("instruction", "embedded\u0000control");
        try { ApiConfig.parse(preferences); throw new AssertionError("Control character accepted"); }
        catch (ExplanationFailure expected) { }
        invalidConfig("unknown", "test-model");
        invalidConfig("../openai", "test-model");
        invalidConfig("", "test-model");
        invalidConfig("openai", "");
        invalidConfig("openai", "model\nprovider=evren");
        System.out.println("Provider config, API encoding and response checks passed.");
    }

    private static ApiConfig config(String provider, String model) throws Exception {
        Properties values = new Properties();
        values.setProperty("provider", provider);
        values.setProperty("model", model);
        values.setProperty("instruction", "Explain in Turkish.");
        return ApiConfig.parse(values);
    }

    private static void invalidConfig(String provider, String model) throws Exception {
        try {
            config(provider, model);
            throw new AssertionError("invalid config accepted");
        } catch (ExplanationFailure expected) { }
    }

    private static void rejected(String body, int status) throws Exception {
        try {
            ChatRequest.decode(body, status);
            throw new AssertionError("invalid or incomplete response accepted");
        } catch (ExplanationFailure expected) { }
    }

    private static void require(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
}
