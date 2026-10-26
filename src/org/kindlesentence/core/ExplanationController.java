package org.kindlesentence.core;

import javax.swing.SwingUtilities;

public final class ExplanationController {
    private final SelectionPreview view;
    private final ExplanationRequest.Factory factory;
    private String selection;
    private boolean active;
    private long generation;
    private ExplanationRequest current;
    private boolean started;

    public ExplanationController(SelectionPreview view, ExplanationRequest.Factory factory) {
        this.view = view;
        this.factory = factory;
    }

    public void select(String text) {
        if (text != null && text.equals(selection)) return;
        cancel();
        selection = text;
        view.showSelection(text);
        view.showStatus("Selected text");
        startIfReady();
    }

    public void setActive(boolean value) {
        active = value;
        if (!value) cancel();
        else startIfReady();
    }

    public void clear() {
        active = false;
        cancel();
        selection = null;
        view.clear();
    }

    private void cancel() {
        generation++;
        if (current != null) current.cancel();
        current = null;
        started = false;
    }

    private void startIfReady() {
        if (!active || started || selection == null || selection.trim().isEmpty()) return;
        started = true;
        if (selection.length() > 8000) {
            view.showStatus("Please select a shorter passage.");
            return;
        }
        final long ticket = generation;
        final ExplanationRequest request = factory.create(selection);
        current = request;
        view.showStatus("Explaining...");
        Thread worker = new Thread(() -> {
            String answer = null;
            String error = null;
            try {
                answer = request.execute();
            } catch (Exception failure) {
                error = failure instanceof ExplanationFailure
                        ? failure.getMessage() : "Could not get an explanation. Close and try again.";
            }
            final String result = answer;
            final String message = error;
            SwingUtilities.invokeLater(() -> {
                if (!active || generation != ticket || current != request) return;
                current = null;
                if (message == null) {
                    view.showSelection(result);
                    view.showStatus("Explanation");
                } else {
                    view.showSelection(message);
                    view.showStatus("Could not explain");
                }
            });
        }, "sentence-explanation");
        worker.setDaemon(true);
        worker.start();
    }
}
