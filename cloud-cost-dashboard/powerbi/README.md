# Power BI version

This is a native, editable Power BI project: six tables, five single-direction relationships, eight DAX measures and three report pages. The CSV files are in `../data`.

Open `CloudCosts.pbip` in a recent Power BI Desktop release with Power BI project / enhanced report format support enabled. In **Transform data → Manage parameters**, set `DataFolder` to the full path of this project's `data` folder, ending with `/` or `\`. Apply changes and refresh. The initial parameter points to the folder where this project was built.

The account and date slicers filter the model. Service or department selections intentionally leave the account budget measure blank: no service-level or department-level budget exists in the source. Budget assumptions are imported from `budgets.csv`; edit that CSV and refresh to change the Power BI scenario. Browser budget edits do not modify these files.

Report pages: Overview, Cost drivers, and Allocation & data coverage. All amounts are USD. Source dates are **1–19 June 2024**, not a complete month. Budgets are illustrative, not approved company budgets. There is no forecast or claimed savings.

The 28 report/project JSON files passed Microsoft's published schema validation. The CSV keys and model relationships also passed automated checks. **Power BI Desktop was not available for opening and refreshing the project in this environment.** Its native rendering and DAX execution therefore remain unverified. The browser dashboard and Excel version were independently tested and are ready to use.

Model definitions: `CloudCosts.SemanticModel/model.bim`; readable measures: `CloudCosts.SemanticModel/measures.dax`. Recreate the project with `python src/build_powerbi.py` from the project root. This also resets the data-folder parameter to that root.

Format reference: [Microsoft Power BI project documentation](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview).
