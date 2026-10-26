package org.kindlesentence.nativeui;

import com.amazon.ebook.booklet.reader.sdk.BookNavigator;
import com.amazon.ebook.booklet.reader.sdk.ReaderSDK;
import com.amazon.ebook.booklet.reader.sdk.content.Book;
import com.amazon.ebook.booklet.reader.sdk.ui.element.Element;
import com.amazon.ebook.booklet.reader.sdk.ui.SelectionDialogCard;
import com.amazon.ebook.booklet.reader.sdk.ui.SelectionDialogCardProvider;

final class ExplainProvider implements SelectionDialogCardProvider {
    private final ExplainCard card;
    private final ReaderSDK sdk;

    ExplainProvider(ReaderSDK sdk) {
        this.sdk = sdk;
        this.card = new ExplainCard(this::closeCard);
    }

    private void closeCard() {
        if (sdk != null) {
            sdk.Jd().Hz().Vo().closeDialog();
            card.clear();
        }
    }

    @Override
    public void update() {
        try {
            if (sdk == null) {
                card.showStatus("no SDK");
                return;
            }
            BookNavigator navigator = sdk.mH();
            Book book = sdk.mJ();
            if (navigator == null || book == null) {
                card.showStatus("no book");
                return;
            }
            if (!navigator.hasSelection()) {
                card.showStatus("none");
                return;
            }
            Element start = navigator.azE();
            Element end = navigator.azF();
            if (start == null || end == null) {
                card.showStatus("no endpoints");
                return;
            }
            String text = book.q(start.mt(), end.mq());
            if (text == null) {
                card.showStatus("null text");
            } else {
                card.showText(text);
            }
        } catch (Exception failure) {
            card.showStatus("read error");
        }
    }

    @Override
    public SelectionDialogCard amP() {
        return card;
    }

    void clear() {
        card.clear();
    }
}
