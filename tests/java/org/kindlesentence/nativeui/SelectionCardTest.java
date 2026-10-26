package org.kindlesentence.nativeui;

import com.amazon.ebook.booklet.reader.sdk.ui.SelectionDialogCard;
import java.awt.Component;
import java.awt.Container;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import javax.swing.BoxLayout;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.SwingUtilities;
import javax.swing.JScrollPane;
import javax.swing.JTextArea;
import javax.swing.JButton;

public final class SelectionCardTest {
    public static void main(String[] args) throws Exception {
        SwingUtilities.invokeAndWait(() -> {
            ExplainProvider provider = new ExplainProvider(null);
            SelectionDialogCard card = provider.amP();
            JPanel host = new JPanel();
            host.setLayout(new BoxLayout(host, BoxLayout.Y_AXIS));
            host.add(new JLabel("Explain"));
            host.add(card);
            for (int width : new int[] {320, 600, 1072}) {
                host.setSize(width, 400);
                for (int cycle = 0; cycle < 3; cycle++) {
                    provider.update();
                    card.closeDialog();
                    host.remove(card);
                    host.add(card);
                    layout(host);
                    require(card.isActive() && card.amS(), "card remains available");
                    Container panel = (Container) card.getComponent(0);
                    JLabel label = (JLabel) panel.getComponent(0);
                    require("Selection: no SDK".equals(label.getText()), "missing SDK visible");
                    JScrollPane scroll = (JScrollPane) panel.getComponent(1);
                    JTextArea text = (JTextArea) scroll.getViewport().getView();
                    require(!text.isEnabled() && !text.isEditable() && !text.isFocusable(),
                            "text interaction is disabled");
                    require(scroll.isEnabled() && scroll.getVerticalScrollBar().isEnabled(),
                            "scroll controls remain enabled");
                    String selected = "  It’s raining cats and dogs.\nReally!  ";
                    ((ExplainCard) card).showText(selected);
                    card.closeDialog();
                    host.remove(card);
                    host.add(card);
                    layout(host);
                    require(selected.equals(text.getText()), "selection survives native close and reattach");
                    require(text.getWidth() > 0 && text.getHeight() > 0, "text receives space");
                    require(scroll.getViewport().getExtentSize().height > 0, "viewport receives space");
                    BufferedImage image = new BufferedImage(card.getWidth(), card.getHeight(),
                            BufferedImage.TYPE_INT_RGB);
                    Graphics2D graphics = image.createGraphics();
                    card.paint(graphics);
                    graphics.dispose();
                    int dark = 0;
                    int white = 0;
                    for (int y = 0; y < image.getHeight(); y++) {
                        for (int x = 0; x < image.getWidth(); x++) {
                            int rgb = image.getRGB(x, y) & 0xffffff;
                            if (rgb == 0) dark++;
                            if (rgb == 0xffffff) white++;
                        }
                    }
                    require(dark > 20 && white > dark, "text paints on white background");
                    ((ExplainCard) card).showText("New selection");
                    require("New selection".equals(text.getText()), "new text replaces old");
                    provider.update();
                    require(text.getText().isEmpty(), "failed update clears old text");
                    ((ExplainCard) card).showText(selected);
                    provider.clear();
                    require(text.getText().isEmpty(), "provider teardown clears text");
                    StringBuilder longText = new StringBuilder();
                    for (int line = 0; line < 100; line++) longText.append("A long preview line.\n");
                    ((ExplainCard) card).showText(longText.toString());
                    layout(host);
                    scroll.getVerticalScrollBar().setValue(100);
                    layout(host);
                    require(scroll.getViewport().getViewPosition().y > 0,
                            "long text can scroll with disabled text interaction");
                }
            }
            int[] closes = {0};
            ExplainCard closable = new ExplainCard(() -> closes[0]++);
            Container panel = (Container) closable.getComponent(0);
            JButton button = (JButton) panel.getComponent(2);
            button.doClick(0);
            require(closes[0] == 1, "Close calls dismissal exactly once");
        });
        System.out.println("Selection card host checks passed; Kindle rendering remains untested.");
    }

    private static void layout(Container parent) {
        parent.doLayout();
        for (Component child : parent.getComponents()) {
            if (child instanceof Container) layout((Container) child);
        }
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
