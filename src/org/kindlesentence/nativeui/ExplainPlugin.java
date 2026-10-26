package org.kindlesentence.nativeui;

import com.amazon.ebook.booklet.reader.sdk.ReaderContentSDK;
import com.amazon.ebook.booklet.reader.sdk.ReaderPlugin;
import com.amazon.ebook.booklet.reader.sdk.ReaderSDK;
import com.amazon.kindle.reader.commons.providers.Provider;

public final class ExplainPlugin extends ReaderPlugin {
    private ReaderSDK sdk;
    private ExplainProvider provider;

    @Override
    public String getName() {
        return "KindleSentenceExplainPreview";
    }

    @Override
    protected void e(ReaderSDK reader) {
        tH();
        ExplainProvider candidate = new ExplainProvider(reader);
        reader.Jc().a((Provider) candidate);
        sdk = reader;
        provider = candidate;
    }

    @Override
    protected void tH() {
        if (provider != null) {
            try {
                sdk.Jc().b((Provider) provider);
            } finally {
                provider.clear();
                provider = null;
                sdk = null;
            }
        }
    }

    @Override
    protected void a(ReaderContentSDK content) {
    }

    @Override
    protected void tG() {
        if (provider != null) provider.clear();
    }
}
