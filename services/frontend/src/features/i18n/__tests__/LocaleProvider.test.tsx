import { fireEvent, render } from "@testing-library/react";

import { LocaleProvider, useLocale } from "@/features/i18n/LocaleProvider";

function TestComponent() {
  const { locale, toggle } = useLocale();
  return (
    <button type="button" onClick={toggle} data-locale={locale}>
      toggle
    </button>
  );
}

describe("LocaleProvider", () => {
  it("switches document direction", () => {
    const { getByRole } = render(
      <LocaleProvider>
        <TestComponent />
      </LocaleProvider>
    );
    const button = getByRole("button");
    expect(document.documentElement.dir).toBe("ltr");
    fireEvent.click(button);
    expect(button.getAttribute("data-locale")).toBe("fa");
    expect(document.documentElement.dir).toBe("rtl");
  });
});
