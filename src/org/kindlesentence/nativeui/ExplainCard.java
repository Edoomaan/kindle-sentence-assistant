package org.kindlesentence.nativeui;

import com.amazon.ebook.booklet.reader.sdk.ui.SelectionDialogCard;
import java.awt.BorderLayout;
import java.awt.Color;
import javax.swing.SwingUtilities;
import org.kindlesentence.api.ChatRequest;
import org.kindlesentence.core.ExplanationController;
import org.kindlesentence.core.SelectionPreview;

final class ExplainCard extends SelectionDialogCard {
    private final SelectionPreview preview;
    private final ExplanationController controller;
    private boolean requested;
    ExplainCard(Runnable onClose) {
        preview = new SelectionPreview(() -> {
            closeDialog();
            onClose.run();
        });
        controller = new ExplanationController(preview, ChatRequest::new);
        setLayout(new BorderLayout());
        setOpaque(true);
        setBackground(Color.WHITE);
        add(preview, BorderLayout.CENTER);
    }

    void showStatus(String state) {
        controller.clear();
        preview.showStatus("Selection: " + state);
    }

    void showText(String text) {
        controller.select(text);
        SwingUtilities.invokeLater(this::refreshActivity);
    }

    void clear() {
        requested = false;
        controller.clear();
    }

    @Override
    public void ft(boolean value) {
        super.ft(value);
        requested = value;
        if (!value) controller.setActive(false);
        else SwingUtilities.invokeLater(this::refreshActivity);
    }

    private void refreshActivity() {
        controller.setActive(requested && isShowing());
    }

    @Override
    public void addNotify() {
        super.addNotify();
        SwingUtilities.invokeLater(this::refreshActivity);
    }

    @Override
    public void removeNotify() {
        controller.setActive(false);
        super.removeNotify();
    }

    @Override
    public void setVisible(boolean visible) {
        super.setVisible(visible);
        if (controller != null) {
            if (!visible) controller.setActive(false);
            else SwingUtilities.invokeLater(this::refreshActivity);
        }
    }

    @Override
    public void closeDialog() {
        requested = false;
        controller.setActive(false);
        super.closeDialog();
    }

    @Override
    public String amT() {
        return "KINDLE_SENTENCE_EXPLAIN_PREVIEW";
    }

    @Override
    public String amR() {
        return "Explain";
    }

    @Override
    public boolean amS() {
        return true;
    }

    @Override
    public int getPriority() {
        return 1100;
    }
}
