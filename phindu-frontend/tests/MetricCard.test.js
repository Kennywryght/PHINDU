import { describe, it, expect } from "vitest";
import { render } from "@testing-library/svelte";
import MetricCard from "../src/components/MetricCard.svelte";

describe("MetricCard", () => {
  it("renders title and formatted number", () => {
    const { getByText } = render(MetricCard, {
      props: { title: "Total Revenue", value: 3500 },
    });
    expect(getByText("Total Revenue")).toBeInTheDocument();
    // toLocaleString adds comma for thousands in most locales
    expect(getByText(/3[,.]?500/)).toBeInTheDocument();
  });

  it("renders prefix (e.g. MWK) when provided", () => {
    const { container } = render(MetricCard, {
      props: { title: "Revenue", value: 1500, prefix: "MWK" },
    });
    expect(container.querySelector(".prefix").textContent).toBe("MWK");
  });

  it("renders suffix (e.g. %) when provided", () => {
    const { container } = render(MetricCard, {
      props: { title: "Profit Margin", value: 25.5, suffix: "%" },
    });
    expect(container.querySelector(".suffix").textContent).toBe("%");
  });

  it("adds highlight class when highlight=true", () => {
    const { container } = render(MetricCard, {
      props: { title: "Profit", value: 8000, highlight: true },
    });
    const card = container.querySelector(".metric-card");
    expect(card.classList.contains("highlight")).toBe(true);
  });

  it("does NOT add highlight class by default", () => {
    const { container } = render(MetricCard, {
      props: { title: "Revenue", value: 1000 },
    });
    const card = container.querySelector(".metric-card");
    expect(card.classList.contains("highlight")).toBe(false);
  });

  it("formats decimals with max 2 fraction digits", () => {
    const { container } = render(MetricCard, {
      props: { title: "Profit", value: 1234.5678 },
    });
    const number = container.querySelector(".number").textContent;
    // Should NOT show more than 2 decimal places
    expect(number).not.toMatch(/\.\d{3,}/);
  });

  it("renders string values as-is (no formatting)", () => {
    const { container } = render(MetricCard, {
      props: { title: "Status", value: "Active" },
    });
    expect(container.querySelector(".number").textContent).toBe("Active");
  });
});