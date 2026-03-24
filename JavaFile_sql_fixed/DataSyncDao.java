package com.sbtr.base.dao.impl;

import com.base.dao.impl.BaseHibernateDao;
import com.sbtr.base.dao.IDataSyncDao;
import com.sbtr.base.domain.DataSync;
import org.hibernate.SQLQuery;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

@Transactional
@Repository("DataSyncDao")
public class DataSyncDao  extends BaseHibernateDao<DataSync, String> implements IDataSyncDao {

	@Override
	public String getEndUpdateTime() {
		List<Date> list = new ArrayList<Date>();
		String sql = "select end_update_time from syncrecord";
		SQLQuery query = getSession().createSQLQuery(sql);
		list = query.list();
		
		if(list.size() > 0)
		{
			return list.get(0).toString();
		}
		else
		{
			return null;
		}
	}

	@Override
	public List<String> getDataSyncInsertSql(Date endUpdateTime) throws Exception {
		List<String> sqlList = new ArrayList<String>();
		return sqlList;
	}
	
	public String getInsertSql(Object obj, String tableName) throws Exception
	{
		Class cls = obj.getClass();
		String sql = "insert into " + tableName + " (";
		Field[] fields = cls.getDeclaredFields();
		String columnName="";
		String columnValue="";
		Object objs[] = new Object[fields.length];
		for(int i=0; i<fields.length; i++)
		{
			String fieldName=fields[i].getName();
			String fieldMethodOfget = fieldName.substring(0, 1).toUpperCase() + fieldName.substring(1, fieldName.length());
			Method methodofget = cls.getMethod("get"+fieldMethodOfget, null);
			Object value = methodofget.invoke(obj, null);
			if(value!=null){
				columnName += ","+fieldName;
				if(value.getClass().getSimpleName().equals("String")){
					columnValue += ",'" + value + "'";
				}else{
					columnValue += "," + value;
				}
			}
		}
		columnName = columnName.substring(1, columnName.length());
		sql += columnName + ") values (";
		columnValue = columnValue.substring(1, columnValue.length());
		sql += columnValue + ")";
		return sql;
	}

	@Override
	public List<String> getDataSyncUpdateSql(Date endUpdateTime)
			throws Exception {
		List<String> sqlList = null;
		return sqlList;
	}
	
	private String getUpdateSql(Object obj, String tableName) throws Exception {
		Class cls = obj.getClass();
		String sql = "UPDATE " + tableName + " SET ";
		Field[] fields = cls.getDeclaredFields();
		String id="";
		String columnValue="";
		Object objs[] = new Object[fields.length];
		for(int i=0; i<fields.length; i++)
		{
			String fieldName=fields[i].getName();
			String fieldMethodOfget = fieldName.substring(0, 1).toUpperCase() + fieldName.substring(1, fieldName.length());
			Method methodofget = cls.getMethod("get"+fieldMethodOfget, null);
			Object value = methodofget.invoke(obj, null);
			if(fieldName != "id"){
				if(value!=null){
					if(value.getClass().getSimpleName().equals("String") || value.getClass().getSimpleName().equals("Timestamp")){
						sql += fieldName +"='" + value + "',";
					}else{
						sql += fieldName + "=" + value + ",";
					}
				}
			}else{
				id += value;
			}
		}
		sql = sql.substring(0, sql.length()-1);
		sql += " WHERE id='" + id + "'";
		return sql;
	}

	public List<?> getInsertObjectList(String tableName, Class<?> clazz, Date endUpdateTime)
	{
		String sql = "select * from " + tableName + " where create_date>? and modifed_date is null";
		SQLQuery query = getSession().createSQLQuery(sql);
		query.setParameter(0, endUpdateTime);
		query.addEntity(clazz);
		List<Object> list =  query.list();
		return list;
	}
	
	public List<?> getUpdateObjectList(String tableName, Class<?> clazz, Date endUpdateTime)
	{
		String sql = "select * from " + tableName + " where modifed_date>?";
		SQLQuery query = getSession().createSQLQuery(sql);
		query.setParameter(0, endUpdateTime);
		query.addEntity(clazz);
		List<Object> list =  query.list();
		return list;
	}

}