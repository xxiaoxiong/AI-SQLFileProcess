package com.sbtr.database.basicinfo.dao.impl;

import com.base.dao.impl.BaseHibernateDao;
import com.sbtr.common.PageUtils;
import com.sbtr.common.StringHelper;
import com.sbtr.database.basicinfo.dao.IDepartmentDao;
import com.sbtr.database.basicinfo.domain.Department;
import com.sbtr.database.basicinfo.domain.DepartmentCondition;
import org.hibernate.Criteria;
import org.hibernate.SQLQuery;
import org.hibernate.criterion.Restrictions;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Transactional
@Repository("DepartmentDao")
public class DepartmentDao extends BaseHibernateDao<Department, String> implements IDepartmentDao {
	
	@Autowired
	@Qualifier("jdbcTemplate")
	private JdbcTemplate jdbcTemplate;

	@Override
	public Boolean isUnique(Department department) {
		Criteria c = getSession().createCriteria(Department.class);
		c.add(Restrictions.or(
				Restrictions.eq("department_name", department.getDepartment_name())));
		
		List<Department> list = c.list();
		return StringHelper.isUnique(list.size(), department.getId());
	}

	@Override
	public List<Department> listByCondition(DepartmentCondition condition) {
		String id = StringHelper.trimBlanks(condition.getId());
		String department_code =  StringHelper.trimBlanks(condition.getDepartment_code());
		String department_name =  StringHelper.trimBlanks(condition.getDepartment_name());
		String parent_department_code =  StringHelper.trimBlanks(condition.getParent_department_code());
		String parent_department_name =  StringHelper.trimBlanks(condition.getParent_department_name());
		String organization_code =  StringHelper.trimBlanks(condition.getOrganization_code());
		String organization_name =  StringHelper.trimBlanks(condition.getOrganization_name());
		String type =  StringHelper.trimBlanks(condition.getType());

		StringBuilder sql = new StringBuilder("select * from rs_department where 1=1 and status=1 ");
		List<Object> params = new ArrayList<>();

		if(StringHelper.isNotEmpty(id)){
			sql.append(" and id like ? ");
			params.add("%" + id + "%");
		}
		if(StringHelper.isNotEmpty(department_name)){
			sql.append(" and department_name like ? ");
			params.add("%" + department_name + "%");
		}
		if(StringHelper.isNotEmpty(department_code)){
			sql.append(" and department_code = ? ");
			params.add(department_code);
		}
		if(StringHelper.isNotEmpty(parent_department_name)){
			sql.append(" and parent_department_name like ? ");
			params.add("%" + parent_department_name + "%");
		}
		if(StringHelper.isNotEmpty(parent_department_code)){
			sql.append(" and parent_department_code = ? ");
			params.add(parent_department_code);
		}
		if(StringHelper.isNotEmpty(organization_name)){
			sql.append(" and organization_name like ? ");
			params.add("%" + organization_name + "%");
		}
		if(StringHelper.isNotEmpty(organization_code)){
			sql.append(" and organization_code = ? ");
			params.add(organization_code);
		}
		if(StringHelper.isNotEmpty(type)){
			sql.append(" and type = ? ");
			params.add(type);
		}
		
		SQLQuery query = getSession().createSQLQuery(sql.toString());
		query.addEntity(Department.class);
		for (int i = 0; i < params.size(); i++) {
			query.setParameter(i, params.get(i));
		}
		
		List<Department> list =  query.list();
		return list;
	}

	@Override
	public List<Department> findAllEnableDepartment() {
		String sql = "select * from rs_department where status=1 and type='1' ";
		SQLQuery query = getSession().createSQLQuery(sql);
		query.addEntity(Department.class);
		return query.list();
	}

	@Override
	public void listByConditionPage(
			DepartmentCondition condition, PageUtils<Department> page) {

		String id = StringHelper.trimBlanks(condition.getId());
		String department_code =  StringHelper.trimBlanks(condition.getDepartment_code());
		String department_name =  StringHelper.trimBlanks(condition.getDepartment_name());
		String parent_department_code =  StringHelper.trimBlanks(condition.getParent_department_code());
		String parent_department_name =  StringHelper.trimBlanks(condition.getParent_department_name());
		String organization_code =  StringHelper.trimBlanks(condition.getOrganization_code());
		String organization_name =  StringHelper.trimBlanks(condition.getOrganization_name());
		String type =  StringHelper.trimBlanks(condition.getType());

		StringBuilder sql = new StringBuilder("from rs_department where 1=1 and status=1 ");
		List<Object> params = new ArrayList<>();

		if(StringHelper.isNotEmpty(id)){
			sql.append(" and id like ? ");
			params.add("%" + id + "%");
		}
		if(StringHelper.isNotEmpty(department_name)){
			sql.append(" and department_name like ? ");
			params.add("%" + department_name + "%");
		}
		if(StringHelper.isNotEmpty(department_code)){
			sql.append(" and department_code = ? ");
			params.add(department_code);
		}
		if(StringHelper.isNotEmpty(parent_department_name)){
			sql.append(" and parent_department_name like ? ");
			params.add("%" + parent_department_name + "%");
		}
		if(StringHelper.isNotEmpty(parent_department_code)){
			sql.append(" and parent_department_code = ? or department_code = ? ");
			params.add(parent_department_code);
			params.add(parent_department_code);
		}
		if(StringHelper.isNotEmpty(organization_name)){
			sql.append(" and organization_name like ? ");
			params.add("%" + organization_name + "%");
		}
		if(StringHelper.isNotEmpty(organization_code)){
			sql.append(" and organization_code = ? ");
			params.add(organization_code);
		}
		if(StringHelper.isNotEmpty(type)){
			sql.append(" and type = ? ");
			params.add(type);
		}

		String orderSql="";
		if(!"".equals(page.getSortColumn())){
			orderSql=" order by "+page.getSortColumn();
		}

		String querySql = "select * "+sql.toString()+orderSql +" limit ?, ?";//分页查询
		String countSql = "select count(*) "+sql.toString();//查询总记录
		
		Integer rowCount = jdbcTemplate.queryForObject(countSql, params.toArray(), Integer.class);
		
		List<Department> list = new ArrayList<Department>();
		if(rowCount > 0){//存在数据进行查询，否则不进行查询
			SQLQuery query = getSession().createSQLQuery(querySql);
			query.addEntity(Department.class);
			int paramIndex = 0;
			for (; paramIndex < params.size(); paramIndex++) {
				query.setParameter(paramIndex, params.get(paramIndex));
			}
			query.setInteger(paramIndex++, page.getStartIndex());
			query.setInteger(paramIndex, page.getPageSize());
			list =  query.list();
		}
		page.setTotal(rowCount);
		page.setRows(list);
	}
//	public void listByConditionPage_Oracle(
//			DepartmentCondition condition, PageUtils<Department> page) {
//
//		String id = StringHelper.trimBlanks(condition.getId());
//		String code =  StringHelper.trimBlanks(condition.getDepartment_code());
//		String name =  StringHelper.trimBlanks(condition.getDepartment_name());
//
//		//oracle分页查询包装头-----------
//		String sql = " from (" +
//				"select rownum as fnorder, t.* from (" +
//				"select coret.* from rs_department coret ";
//		sql=sql+"where 1=1 and status=1 and type='1' ";
//		//-----------oracle分页查询包装头
//
//		if(StringHelper.isNotEmpty(id)){
//			sql+= " and coret.id like '%" + id+"%' ";
//		}
//		if(StringHelper.isNotEmpty(code)){
//			sql+= " and coret.department_code like '%" + code+"%' ";
//		}
//		if(StringHelper.isNotEmpty(name)){
//			sql+= " and coret.department_name like '%" + name+"%' ";
//		}
//
//		//oracle分页查询包装尾部-----------
//		String orderSql="";
//		if(!"".equals(page.getSortColumn())){
//			orderSql=" order by "+page.getSortColumn();
//		}
//		String querySql = "select * "+
//				sql+
//				" "+orderSql+") t "+
//				" ) a where a.fnorder>"+Integer.toString(page.getStartIndex())+" and a.fnorder<="+Integer.toString((page.getStartIndex()+page.getPageSize()));//查询距离列表
//		String countSql = "select count(*) "+sql+
//				" ) t "+
//				" ) a ";//查询总记录
//		//-----------oracle分页查询包装尾部
//
//		Integer rowCount = jdbcTemplate.queryForObject(countSql,Integer.class);
//
//		List<Department> list = new ArrayList<Department>();
//		if(rowCount > 0){//存在数据进行查询，否则不进行查询
//			SQLQuery query = getSession().createSQLQuery(querySql);
//			query.addEntity(Department.class);
//			list =  query.list();
//		}
//		page.setTotal(rowCount);
//		page.setRows(list);
//	}

	@Override
	public List<Department> listByCode(String code) {
		String sql = "";
		code = StringHelper.trimBlanks(code);

		sql = "select * from rs_department where status=1 and type='1' and department_code = ? ";
		SQLQuery query = getSession().createSQLQuery(sql);
		query.addEntity(Department.class);
		query.setParameter(0, code);
		return query.list();
	}

	@Override
	public List<Department> listByOrgCodes(String codes) {
		String sql = "";
		codes = StringHelper.trimBlanks(codes);
		String[] codeArray = codes.split(",");
		StringBuilder placeholders = new StringBuilder();
		for (int i = 0; i < codeArray.length; i++) {
			if (i > 0) placeholders.append(",");
			placeholders.append("?");
		}
		sql = "select * from rs_department where status=1 and type='1' and organization_code in (" + placeholders + ") ";
		SQLQuery query = getSession().createSQLQuery(sql);
		query.addEntity(Department.class);
		for (int i = 0; i < codeArray.length; i++) {
			query.setParameter(i, codeArray[i]);
		}
		return query.list();
	}

	@Override
	public List<Department> listDuplicate() {
		String sql = "select * FROM rs_department WHERE status=1 and type='1' and department_name IN" +
				" (SELECT department_name FROM rs_department GROUP BY department_name HAVING COUNT(department_name) > 1)" +
				" OR department_code IN" +
				" (SELECT department_code FROM rs_department GROUP BY department_code HAVING COUNT(department_code) > 1)";
		SQLQuery query = getSession().createSQLQuery(sql);
		query.addEntity(Department.class);
		List<Department> list =  query.list();
		return list;
	}

	@Override
	public void pageDuplicate(PageUtils<Department> page) {
		String sql = "FROM rs_department WHERE status=1 and type='1' and department_name IN" +
				" (SELECT department_name FROM rs_department GROUP BY department_name HAVING COUNT(department_name) > 1)" +
				" OR department_code IN" +
				" (SELECT department_code FROM rs_department GROUP BY department_code HAVING COUNT(department_code) > 1)";

		String orderSql="";
		if(!"".equals(page.getSortColumn())){
			orderSql=" order by "+page.getSortColumn();
		}else{
			orderSql=" order by department_name, department_code ";
		}

		String querySql = "select * "+sql+orderSql +" limit ?, ?";//分页查询
		String countSql = "select count(*) "+sql;//查询总记录
		Integer rowCount = jdbcTemplate.queryForObject(countSql,Integer.class);

		List<Department> resultList = new ArrayList();
		List<Department> list = new ArrayList<Department>();
		if(rowCount > 0){//存在数据进行查询，否则不进行查询
			SQLQuery query = getSession().createSQLQuery(querySql);
			query.addEntity(Department.class);
			query.setInteger(0, page.getStartIndex());
			query.setInteger(1, page.getPageSize());
			resultList =  query.list();

		}
		page.setTotal(rowCount);
		page.setRows(resultList);
	}

	@Override
	public void deleteAll() {
		String sql = "delete from rs_department";
		jdbcTemplate.update(sql);
	}
}