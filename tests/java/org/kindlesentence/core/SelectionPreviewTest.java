package org.kindlesentence.core;

import javax.swing.SwingUtilities;

public final class SelectionPreviewTest {
    public static void main(String[] args) throws Exception {
        SwingUtilities.invokeAndWait(() -> {
            SelectionPreview view = new SelectionPreview();
            require(!view.hasSelection(), "starts without selection");
            String original = "  It’s raining cats and dogs.\nReally!  ";
            view.showSelection(original);
            require(original.equals(view.selectedText()), "preserves exact selection");
            view.showSelection("A different sentence.");
            require("A different sentence.".equals(view.selectedText()), "replaces previous text");
            view.clear();
            require(!view.hasSelection() && view.selectedText().isEmpty(), "clears on close");
            view.showSelection(original);
            view.showSelection(null);
            require(!view.hasSelection() && view.selectedText().isEmpty(), "missing selection clears stale text");
            view.showSelection(" \n\t");
            require(!view.hasSelection(), "whitespace is not a selection");
        });
        System.out.println("SelectionPreview checks passed.");
    }

    private static void require(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }
}
