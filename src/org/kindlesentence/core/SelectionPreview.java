package org.kindlesentence.core;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Dimension;
import java.awt.Font;
import javax.swing.JLabel;
import javax.swing.JButton;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTextArea;

public final class SelectionPreview extends JPanel {
    private final JTextArea text = new JTextArea();
    private final JLabel status = new JLabel("Selected text");
    private boolean hasSelection;

    public SelectionPreview() {
        this(() -> { });
    }

    public SelectionPreview(Runnable onClose) {
        super(new BorderLayout());
        setOpaque(true);
        setBackground(Color.WHITE);
        setPreferredSize(new Dimension(320, 240));
        status.setForeground(Color.BLACK);
        status.setFont(new Font("SansSerif", Font.PLAIN, 7));
        text.setFont(new Font("SansSerif", Font.PLAIN, 8));
        text.setForeground(Color.BLACK);
        text.setBackground(Color.WHITE);
        text.setOpaque(true);
        text.setEditable(false);
        text.setEnabled(false);
        text.setDisabledTextColor(Color.BLACK);
        text.setFocusable(false);
        text.setLineWrap(true);
        text.setWrapStyleWord(true);
        add(status, BorderLayout.NORTH);
        add(new JScrollPane(text), BorderLayout.CENTER);
        JButton close = new JButton("Close");
        close.setFont(new Font("SansSerif", Font.PLAIN, 8));
        close.setPreferredSize(new Dimension(120, 56));
        close.addActionListener(event -> onClose.run());
        add(close, BorderLayout.SOUTH);
    }

    public void showSelection(String selectedText) {
        hasSelection = selectedText != null && !selectedText.trim().isEmpty();
        text.setText(hasSelection ? selectedText : "");
        text.setCaretPosition(0);
        revalidate();
        repaint();
    }

    public void showStatus(String message) {
        status.setText(message);
    }

    public boolean hasSelection() {
        return hasSelection;
    }

    public String selectedText() {
        return text.getText();
    }

    public void clear() {
        showSelection(null);
    }
}
