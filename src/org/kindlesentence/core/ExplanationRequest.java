package org.kindlesentence.core;

public interface ExplanationRequest {
    String execute() throws Exception;
    void cancel();

    interface Factory {
        ExplanationRequest create(String selectedText);
    }
}
