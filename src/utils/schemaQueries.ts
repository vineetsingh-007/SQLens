import { DatasetTable, ColumnInfo } from '../types/dataset';

/**
 * Dynamically generates 4-6 natural, dataset-specific questions based on the table schema,
 * column data types, and names.
 */
export function generateSchemaQueries(tables?: DatasetTable[]): string[] {
  if (!tables || tables.length === 0) {
    return ['Ask a question about your data'];
  }

  // Pick primary table (sort by row_count or first)
  const primaryTable = [...tables].sort((a, b) => b.row_count - a.row_count)[0] || tables[0];
  const rawTableName = primaryTable.table_name || 'records';
  const columns = primaryTable.columns_json || [];

  if (!columns || columns.length === 0) {
    return ['Ask a question about your data'];
  }

  const cleanName = (str: string): string => {
    return str
      .replace(/_/g, ' ')
      .replace(/([a-z])([A-Z])/g, '$1 $2')
      .toLowerCase()
      .trim();
  };

  const getPluralEntity = (tbl: string): string => {
    const cleaned = cleanName(tbl);
    if (cleaned.endsWith('s')) return cleaned;
    if (cleaned.endsWith('y')) return cleaned.slice(0, -1) + 'ies';
    return cleaned + 's';
  };

  const entityName = getPluralEntity(rawTableName);

  const dateCols: ColumnInfo[] = [];
  const numericCols: ColumnInfo[] = [];
  const catCols: ColumnInfo[] = [];
  const flagCols: ColumnInfo[] = [];
  const entityCols: ColumnInfo[] = [];

  const ignoreIdRegex = /^(id|_id|uuid|created_by|updated_by|index|row_id)$/i;

  columns.forEach((col) => {
    const nameLower = col.name.toLowerCase();
    const typeLower = (col.type || '').toLowerCase();

    if (ignoreIdRegex.test(nameLower)) return;

    // Date / Time
    if (
      typeLower.includes('date') ||
      typeLower.includes('time') ||
      typeLower.includes('year') ||
      typeLower.includes('month') ||
      nameLower.includes('date') ||
      nameLower.includes('year') ||
      nameLower.includes('month') ||
      nameLower.includes('created_at')
    ) {
      dateCols.push(col);
      return;
    }

    // Flag / Binary / Boolean
    if (
      typeLower.includes('bool') ||
      nameLower.startsWith('is_') ||
      nameLower.startsWith('has_') ||
      ['purchased', 'churned', 'active', 'completed', 'subscribed', 'paid', 'status'].includes(nameLower)
    ) {
      flagCols.push(col);
      return;
    }

    // Numeric (excluding obvious IDs or zipcodes)
    if (
      (typeLower.includes('int') ||
        typeLower.includes('float') ||
        typeLower.includes('double') ||
        typeLower.includes('num') ||
        typeLower.includes('decimal') ||
        typeLower.includes('real')) &&
      !nameLower.endsWith('_id') &&
      !nameLower.includes('zip') &&
      !nameLower.includes('code') &&
      !nameLower.includes('phone')
    ) {
      numericCols.push(col);
      return;
    }

    // Categorical
    if (
      typeLower.includes('char') ||
      typeLower.includes('text') ||
      typeLower.includes('string') ||
      ['category', 'gender', 'sex', 'region', 'country', 'city', 'state', 'department', 'education', 'status', 'brand', 'model', 'segment', 'tier', 'role', 'genre', 'channel', 'payment', 'vendor', 'type', 'class', 'group', 'product', 'customer', 'user'].some((k) => nameLower.includes(k))
    ) {
      if (['product', 'customer', 'user', 'employee', 'item', 'vendor'].some((k) => nameLower.includes(k))) {
        entityCols.push(col);
      }
      catCols.push(col);
      return;
    }
  });

  const generatedQuestions: string[] = [];

  // 1. Total Count / Overview
  generatedQuestions.push(`How many ${entityName} are there?`);

  // 2. Categorical Breakdown (e.g., "Show customers by gender." or "Show sales by category.")
  if (catCols.length > 0) {
    const mainCat = catCols[0];
    const catName = cleanName(mainCat.display_name || mainCat.name);
    if (numericCols.length > 0) {
      const mainNum = numericCols[0];
      const numName = cleanName(mainNum.display_name || mainNum.name);
      generatedQuestions.push(`Show ${numName} by ${catName}.`);
    } else {
      generatedQuestions.push(`Show ${entityName} by ${catName}.`);
    }
  }

  // 3. Highest / Top Ranking (e.g., "Which products have the highest sales?")
  if (numericCols.length > 0) {
    const highNum =
      numericCols.find((c) =>
        ['sales', 'revenue', 'price', 'amount', 'salary', 'score', 'total'].some((k) =>
          c.name.toLowerCase().includes(k)
        )
      ) || numericCols[0];
    const numName = cleanName(highNum.display_name || highNum.name);

    if (entityCols.length > 0 || catCols.length > 0) {
      const groupCol = entityCols[0] || catCols[0];
      const groupName = getPluralEntity(cleanName(groupCol.display_name || groupCol.name));
      generatedQuestions.push(`Which ${groupName} have the highest ${numName}?`);
    } else {
      generatedQuestions.push(`What is the average ${numName}?`);
    }
  }

  // 4. Average / Aggregation (e.g., "What is the average age?" or "What is the average product price?")
  if (numericCols.length > 0) {
    const avgNum =
      numericCols.find((c) =>
        ['age', 'price', 'salary', 'cost', 'amount', 'score'].some((k) =>
          c.name.toLowerCase().includes(k)
        )
      ) || numericCols[numericCols.length - 1];
    const numName = cleanName(avgNum.display_name || avgNum.name);
    const avgQ = `What is the average ${numName}?`;
    if (!generatedQuestions.includes(avgQ)) {
      generatedQuestions.push(avgQ);
    }
  }

  // 5. Binary / Flag condition (e.g., "How many customers made a purchase?")
  if (flagCols.length > 0) {
    const flag = flagCols[0];
    const flagName = flag.name.toLowerCase();
    if (flagName.includes('purchase')) {
      generatedQuestions.push(`How many ${entityName} made a purchase?`);
    } else if (flagName.includes('active')) {
      generatedQuestions.push(`How many ${entityName} are active?`);
    } else {
      generatedQuestions.push(`Show ${entityName} where ${cleanName(flag.name)} is true.`);
    }
  }

  // 6. Time-based trend (e.g., "Show monthly sales" or "Show sales by date")
  if (dateCols.length > 0) {
    const dateCol = dateCols[0];
    const dateName = cleanName(dateCol.display_name || dateCol.name);
    if (numericCols.length > 0) {
      const numName = cleanName(numericCols[0].display_name || numericCols[0].name);
      generatedQuestions.push(`Show ${numName} by ${dateName}.`);
    } else {
      generatedQuestions.push(`Show ${entityName} by ${dateName}.`);
    }
  }

  // 7. Second Categorical breakdown if questions < 5
  if (catCols.length > 1 && generatedQuestions.length < 5) {
    const secCat = catCols[1];
    const catName = cleanName(secCat.display_name || secCat.name);
    const q = `Show ${entityName} by ${catName}.`;
    if (!generatedQuestions.includes(q)) {
      generatedQuestions.push(q);
    }
  }

  const uniqueQuestions = Array.from(new Set(generatedQuestions)).slice(0, 6);

  if (uniqueQuestions.length === 0) {
    return ['Ask a question about your data'];
  }

  return uniqueQuestions;
}
